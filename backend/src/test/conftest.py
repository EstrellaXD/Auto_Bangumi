"""Shared test fixtures for AutoBangumi test suite."""

import pytest
from unittest.mock import AsyncMock, patch

from sqlmodel import Session, SQLModel, create_engine

from module.models.config import Config


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
