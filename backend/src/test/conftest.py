"""Shared test fixtures for AutoBangumi test suite."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, StaticPool
from sqlmodel import SQLModel, create_engine

from module.api import v1
from module.database import Database, get_db
from module.models import ResponseModel
from module.models.config import Config
from module.security.api import get_current_user

# ---------------------------------------------------------------------------
# Download client cache reset
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_downloader_client_cache():
    """Clear the module-level concrete-client cache between tests.

    DownloadClient reuses one concrete client across context-manager blocks
    (session reuse, #1039 / #900); the cache would otherwise leak a mock from
    one test into the next.
    """
    from module.downloader.download_client import _reset_client_cache

    _reset_client_cache()
    yield
    _reset_client_cache()


# ---------------------------------------------------------------------------
# Database Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _bind_bare_database(tmp_path, monkeypatch):
    """Point every bare ``Database()`` at a per-test temp-file SQLite DB.

    A file DB with NullPool works from both pytest-asyncio's loop and the
    TestClient's loop (each connection is independent and opened lazily in the
    active loop), so it is safe for both sync and async tests. Tables are
    created up front with a sync engine so this fixture stays synchronous and
    usable by sync tests. Direct-repo tests that pass ``Database(engine=...)``
    or use ``db_session`` bypass this and get their own in-memory DB.
    """
    db_file = tmp_path / "ab_test.db"
    sync_engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(sync_engine)
    sync_engine.dispose()

    async_engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file}", poolclass=NullPool
    )
    factory = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr("module.database.combine.async_session_factory", factory)
    monkeypatch.setattr("module.database.combine.async_engine", async_engine)
    yield


@pytest_asyncio.fixture
async def db_engine():
    """In-memory async engine shared across connections via StaticPool.

    For direct-repo tests that construct repositories or ``Database(engine=...)``
    explicitly. Fresh per test for isolation.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Provide a fresh async database session per test."""
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


# ---------------------------------------------------------------------------
# Settings Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_settings():
    """Provide a Config object with predictable test defaults."""
    return Config()


@pytest.fixture
def mock_settings(test_settings):
    """Patch module.conf.settings globally with test defaults."""
    with patch("module.conf.settings", test_settings):
        with patch("module.conf.config.settings", test_settings):
            yield test_settings


# ---------------------------------------------------------------------------
# Download Client Mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_qb_client():
    """Mock QbDownloader that simulates qBittorrent API responses."""
    from module.downloader import AddResult, RenameOutcome, RenameResult

    client = AsyncMock()
    client.auth.return_value = True
    client.logout.return_value = None
    client.check_host.return_value = True
    client.torrents_info.return_value = []
    client.torrent_exists.return_value = False
    client.torrents_files.return_value = []
    client.torrents_rename_file.return_value = RenameResult(RenameOutcome.RENAMED)
    client.add_torrents.return_value = AddResult.ADDED
    client.torrents_delete.return_value = None
    client.torrents_pause.return_value = None
    client.torrents_resume.return_value = None
    client.rss_set_rule.return_value = None
    client.prefs_init.return_value = None
    client.add_category.return_value = None
    client.get_app_prefs.return_value = {"save_path": "/downloads"}
    client.move_torrent.return_value = None
    client.rss_add_feed.return_value = None
    client.rss_remove_item.return_value = None
    client.rss_get_feeds.return_value = {}
    client.get_download_rule.return_value = {}
    client.get_torrent_path.return_value = "/downloads/Bangumi"
    client.set_category.return_value = None
    client.remove_rule.return_value = None
    return client


# ---------------------------------------------------------------------------
# FastAPI App & Client Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    """Create a FastAPI app with v1 routes and an async get_db override."""
    app = FastAPI()
    app.include_router(v1, prefix="/api")

    async def _override_get_db():
        async with Database() as db:
            yield db

    app.dependency_overrides[get_db] = _override_get_db
    return app


@pytest.fixture
def authed_client(app):
    """TestClient with auth dependency overridden."""

    async def mock_user():
        return "testuser"

    app.dependency_overrides[get_current_user] = mock_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def unauthed_client(app):
    """TestClient without auth (no override)."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Program Mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_program():
    """Mock Program instance for program API tests."""
    program = MagicMock()
    program.is_running = True
    program.first_run = False
    program.startup = AsyncMock(return_value=None)
    program.start = AsyncMock(
        return_value=ResponseModel(
            status=True, status_code=200, msg_en="Started.", msg_zh="已启动。"
        )
    )
    program.stop = AsyncMock(
        return_value=ResponseModel(
            status=True, status_code=200, msg_en="Stopped.", msg_zh="已停止。"
        )
    )
    program.restart = AsyncMock(
        return_value=ResponseModel(
            status=True, status_code=200, msg_en="Restarted.", msg_zh="已重启。"
        )
    )
    program.check_downloader = AsyncMock(return_value=True)
    return program


# ---------------------------------------------------------------------------
# WebAuthn Mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_webauthn():
    """Mock WebAuthn service for passkey tests."""
    service = MagicMock()
    service.generate_registration_options.return_value = {
        "challenge": "test_challenge",
        "rp": {"name": "AutoBangumi", "id": "localhost"},
        "user": {"id": "user_id", "name": "testuser", "displayName": "testuser"},
        "pubKeyCredParams": [{"type": "public-key", "alg": -7}],
        "timeout": 60000,
        "attestation": "none",
    }
    service.generate_authentication_options.return_value = {
        "challenge": "test_challenge",
        "timeout": 60000,
        "rpId": "localhost",
        "allowCredentials": [],
    }
    service.generate_discoverable_authentication_options.return_value = {
        "challenge": "test_challenge",
        "timeout": 60000,
        "rpId": "localhost",
    }
    service.verify_registration.return_value = MagicMock(
        credential_id="cred_id",
        public_key="public_key",
        sign_count=0,
        name="Test Passkey",
        user_id=1,
    )
    service.verify_authentication.return_value = (True, 1)
    return service


# ---------------------------------------------------------------------------
# Download Client Mock (async context manager version)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_download_client():
    """Mock DownloadClient as async context manager."""
    client = AsyncMock()
    client.get_torrent_info.return_value = [
        {
            "hash": "abc123",
            "name": "[TestGroup] Test Anime - 01.mkv",
            "state": "downloading",
            "progress": 0.5,
        }
    ]
    client.pause_torrent.return_value = None
    client.resume_torrent.return_value = None
    client.delete_torrent.return_value = True
    return client
