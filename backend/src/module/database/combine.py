import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from module.models import Bangumi, User

from .aria2 import Aria2GidDatabase
from .auth import AuthDatabase
from .bangumi import BangumiDatabase
from .engine import async_engine, async_session_factory
from .inbox import InboxDatabase
from .llm_credential import LLMCredentialDatabase
from .migrations import (  # noqa: F401  (re-exported for existing importers)
    CURRENT_SCHEMA_VERSION,
    MIGRATIONS,
    TABLE_MODELS,
    create_tables_async,
    run_migrations_async,
)
from .movie import MovieDatabase
from .rss import RSSDatabase
from .torrent import TorrentDatabase
from .user import UserDatabase

logger = logging.getLogger(__name__)


class Database:
    """Async, session-per-operation database facade.

    Used as ``async with Database() as db``; the session lives only for the
    duration of the block. ``session.add`` stays synchronous (it just queues
    the instance); commit/rollback/refresh/close are awaited.
    """

    def __init__(self, engine=None):
        # ``engine`` is a DI seam for tests, which bind to a throwaway async
        # engine; production always uses the shared ``async_session_factory``.
        if engine is None:
            self.session: AsyncSession = async_session_factory()
        else:
            self.session = AsyncSession(engine, expire_on_commit=False)
        self.rss = RSSDatabase(self.session)
        self.torrent = TorrentDatabase(self.session)
        self.bangumi = BangumiDatabase(self.session)
        self.movie = MovieDatabase(self.session)
        self.user = UserDatabase(self.session)
        self.aria2 = Aria2GidDatabase(self.session)
        self.auth = AuthDatabase(self.session)
        self.inbox = InboxDatabase(self.session)
        self.llm_credential = LLMCredentialDatabase(self.session)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    # Session delegates for call sites that operate on the Database directly.
    def add(self, obj):
        self.session.add(obj)

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()

    async def begin_write(self):
        """Acquire the write transaction before invariant-checking reads.

        SQLite's normal deferred transaction lets two writers observe the same
        last-enabled-user state. ``BEGIN IMMEDIATE`` serializes them before the
        first SELECT; other database backends use their normal explicit begin.
        """
        if self.session.in_transaction():
            raise RuntimeError("Write transaction must begin before database access")
        if self.session.get_bind().dialect.name == "sqlite":
            await self.session.execute(text("BEGIN IMMEDIATE"))
        else:
            await self.session.begin()

    async def refresh(self, obj):
        await self.session.refresh(obj)

    async def close(self):
        await self.session.close()

    async def create_table(self):
        await create_tables_async(async_engine)

    async def run_migrations(self):
        await run_migrations_async(async_engine)

    async def drop_table(self):
        async with async_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)

    async def migrate(self):
        # Run migration online
        bangumi_data = await self.bangumi.search_all()
        result = await self.session.execute(text("SELECT * FROM user"))
        user_data = result.mappings().all()
        if not user_data:
            logger.warning("No user data found, skipping migration.")
            return
        readd_bangumi = []
        for bangumi in bangumi_data:
            dict_data = bangumi.dict()
            del dict_data["id"]
            readd_bangumi.append(Bangumi(**dict_data))
        await self.drop_table()
        await self.create_table()
        await self.commit()
        try:
            await self.bangumi.add_all(readd_bangumi)
            self.add(User(**user_data[0]))
            await self.commit()
        except Exception:
            await self.rollback()
            raise
