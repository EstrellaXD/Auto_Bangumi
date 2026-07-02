from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import create_engine

from module.conf import DATA_PATH

# Sync engine (used by Database, which owns a Session)
engine = create_engine(DATA_PATH)

# Async engine (for passkey operations)
ASYNC_DATA_PATH = DATA_PATH.replace("sqlite:///", "sqlite+aiosqlite:///")
async_engine = create_async_engine(ASYNC_DATA_PATH)
async_session_factory = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


@event.listens_for(engine, "connect")
def _set_sqlite_fk_sync(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _set_sqlite_pragmas_async(dbapi_conn, connection_record):
    """Per-connection SQLite pragmas for the async engine.

    The sync stack was implicitly serialized on a single Session. Several
    aiosqlite connections now write concurrently, so WAL (readers never block
    the writer) plus a busy_timeout (a contended write waits instead of raising
    immediately) are required to avoid ``database is locked``.
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


event.listen(async_engine.sync_engine, "connect", _set_sqlite_pragmas_async)
