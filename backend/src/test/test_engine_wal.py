"""Tests for the async engine's SQLite concurrency pragmas (WAL + busy_timeout)."""

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine

from module.database.engine import _set_sqlite_pragmas_async


async def test_async_engine_enables_wal_and_busy_timeout(tmp_path):
    """A file-backed async engine reports WAL journal mode on every connection.

    WAL is a persistent database property, and busy_timeout is per-connection;
    both must hold across independent connections from the pool.
    """
    db_file = tmp_path / "wal_probe.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    event.listen(engine.sync_engine, "connect", _set_sqlite_pragmas_async)
    try:
        for _ in range(2):
            async with engine.connect() as conn:
                journal_mode = (await conn.execute(text("PRAGMA journal_mode"))).scalar()
                busy_timeout = (await conn.execute(text("PRAGMA busy_timeout"))).scalar()
                assert journal_mode == "wal"
                assert busy_timeout == 5000
    finally:
        await engine.dispose()


async def test_in_memory_engine_reports_memory_journal_mode():
    """In-memory SQLite cannot use WAL and reports 'memory' — asserted separately."""
    engine = create_async_engine("sqlite+aiosqlite://")
    event.listen(engine.sync_engine, "connect", _set_sqlite_pragmas_async)
    try:
        async with engine.connect() as conn:
            journal_mode = (await conn.execute(text("PRAGMA journal_mode"))).scalar()
            assert journal_mode == "memory"
    finally:
        await engine.dispose()
