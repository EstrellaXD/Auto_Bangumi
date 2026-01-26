"""Shared test fixtures for AutoBangumi test suite."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from module.api import v1
from module.models.config import Config
from module.models import ResponseModel
from module.security.api import get_current_user


# ---------------------------------------------------------------------------
# Database Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine):
    """Provide a fresh database session per test."""
    with Session(db_engine) as session:
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
    client = AsyncMock()
    client.auth.return_value = True
    client.logout.return_value = None
    client.check_host.return_value = True
    client.torrents_info.return_value = []
    client.torrents_files.return_value = []
    client.torrents_rename_file.return_value = True
    client.add_torrents.return_value = True
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
    """Create a FastAPI app with v1 routes for testing."""
    app = FastAPI()
    app.include_router(v1, prefix="/api")
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
    client.delete_torrent.return_value = None
    return client
