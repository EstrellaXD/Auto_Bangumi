from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from module.models import Bangumi, Passkey, User

from .bangumi import BangumiDatabase
from .engine import async_session_factory, engine as e
from .passkey import PasskeyDatabase
from .rss import RSSDatabase
from .torrent import TorrentDatabase
from .user import UserDatabase


class Database:
    def __init__(self):
        self._session: AsyncSession | None = None
        self.rss: RSSDatabase | None = None
        self.torrent: TorrentDatabase | None = None
        self.bangumi: BangumiDatabase | None = None
        self.user: UserDatabase | None = None
        self.passkey: PasskeyDatabase | None = None

    async def __aenter__(self):
        self._session = async_session_factory()
        self.rss = RSSDatabase(self._session)
        self.torrent = TorrentDatabase(self._session)
        self.bangumi = BangumiDatabase(self._session)
        self.user = UserDatabase(self._session)
        self.passkey = PasskeyDatabase(self._session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()

    async def create_table(self):
        async with e.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async def drop_table(self):
        async with e.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)

    async def commit(self):
        if self._session:
            await self._session.commit()

    async def add(self, obj):
        if self._session:
            self._session.add(obj)
            await self._session.commit()

    async def migrate(self):
        # Run migration online
        bangumi_data = await self.bangumi.search_all()
        readd_bangumi = []
        for bangumi in bangumi_data:
            dict_data = bangumi.dict()
            del dict_data["id"]
            readd_bangumi.append(Bangumi(**dict_data))
        await self.drop_table()
        await self.create_table()
        await self.commit()
        await self.bangumi.add_all(readd_bangumi)
