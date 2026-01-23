from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import create_engine

from module.conf import DATA_PATH

# Sync engine (used by Database which extends Session)
engine = create_engine(DATA_PATH)

# Async engine (for passkey operations)
ASYNC_DATA_PATH = DATA_PATH.replace("sqlite:///", "sqlite+aiosqlite:///")
async_engine = create_async_engine(ASYNC_DATA_PATH)
async_session_factory = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
