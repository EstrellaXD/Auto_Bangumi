from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from module.conf import DATA_PATH

# The whole application runs on the async engine now. DATA_PATH (the sync
# sqlite URL) is kept only to derive the async URL and for the migration tests,
# which build their own throwaway sync engine.
ASYNC_DATA_PATH = DATA_PATH.replace("sqlite:///", "sqlite+aiosqlite:///")
async_engine = create_async_engine(ASYNC_DATA_PATH)
# async_sessionmaker (not the generic ORM sessionmaker) is the type-correct
# factory for an AsyncEngine -- sessionmaker's `bind` overloads only accept a
# sync Engine/Connection.
async_session_factory = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


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
