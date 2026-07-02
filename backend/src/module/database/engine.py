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


@event.listens_for(async_engine.sync_engine, "connect")
def _set_sqlite_fk_async(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
