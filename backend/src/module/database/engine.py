from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, create_engine

from module.conf import DATA_PATH

# Sync engine (for legacy code)
engine = create_engine(DATA_PATH)
db_session = Session(engine)

# Async engine (for passkey and new async code)
ASYNC_DATA_PATH = DATA_PATH.replace("sqlite:///", "sqlite+aiosqlite:///")
async_engine = create_async_engine(ASYNC_DATA_PATH)
async_session_factory = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
