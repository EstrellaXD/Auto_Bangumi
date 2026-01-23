from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from module.conf import DATA_PATH

# Convert sqlite:///path to sqlite+aiosqlite:///path for async support
ASYNC_DATA_PATH = DATA_PATH.replace("sqlite:///", "sqlite+aiosqlite:///")

engine = create_async_engine(
    ASYNC_DATA_PATH,
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-64000")  # 64MB
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async_session_factory = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
