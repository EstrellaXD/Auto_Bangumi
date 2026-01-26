"""Tests for Downloader API endpoints."""

import pytest
from unittest.mock import patch, AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from module.api import v1
from module.security.api import get_current_user


# ---------------------------------------------------------------------------
# Fixtures
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
        },
        {
            "hash": "def456",
            "name": "[TestGroup] Test Anime - 02.mkv",
            "state": "completed",
            "progress": 1.0,
        },
    ]
    client.pause_torrent.return_value = None
    client.resume_torrent.return_value = None
    client.delete_torrent.return_value = None
    return client


# ---------------------------------------------------------------------------
# Auth requirement
# ---------------------------------------------------------------------------


class TestAuthRequired:
    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_get_torrents_unauthorized(self, unauthed_client):
        """GET /downloader/torrents without auth returns 401."""
        response = unauthed_client.get("/api/v1/downloader/torrents")
        assert response.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_pause_torrents_unauthorized(self, unauthed_client):
        """POST /downloader/torrents/pause without auth returns 401."""
        response = unauthed_client.post(
            "/api/v1/downloader/torrents/pause", json={"hashes": ["abc123"]}
        )
        assert response.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_resume_torrents_unauthorized(self, unauthed_client):
        """POST /downloader/torrents/resume without auth returns 401."""
        response = unauthed_client.post(
            "/api/v1/downloader/torrents/resume", json={"hashes": ["abc123"]}
        )
        assert response.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_delete_torrents_unauthorized(self, unauthed_client):
        """POST /downloader/torrents/delete without auth returns 401."""
        response = unauthed_client.post(
            "/api/v1/downloader/torrents/delete",
            json={"hashes": ["abc123"], "delete_files": False},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /downloader/torrents
# ---------------------------------------------------------------------------


class TestGetTorrents:
    def test_get_torrents_success(self, authed_client, mock_download_client):
        """GET /downloader/torrents returns list of torrents."""
        with patch("module.api.downloader.DownloadClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(
                return_value=mock_download_client
            )
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            response = authed_client.get("/api/v1/downloader/torrents")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["hash"] == "abc123"

    def test_get_torrents_empty(self, authed_client, mock_download_client):
        """GET /downloader/torrents returns empty list when no torrents."""
        mock_download_client.get_torrent_info.return_value = []
        with patch("module.api.downloader.DownloadClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(
                return_value=mock_download_client
            )
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            response = authed_client.get("/api/v1/downloader/torrents")

        assert response.status_code == 200
        assert response.json() == []


# ---------------------------------------------------------------------------
# POST /downloader/torrents/pause
# ---------------------------------------------------------------------------


class TestPauseTorrents:
    def test_pause_single_torrent(self, authed_client, mock_download_client):
        """POST /downloader/torrents/pause pauses a single torrent."""
        with patch("module.api.downloader.DownloadClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(
                return_value=mock_download_client
            )
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            response = authed_client.post(
                "/api/v1/downloader/torrents/pause", json={"hashes": ["abc123"]}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["msg_en"] == "Torrents paused"
        mock_download_client.pause_torrent.assert_called_once_with("abc123")

    def test_pause_multiple_torrents(self, authed_client, mock_download_client):
        """POST /downloader/torrents/pause pauses multiple torrents."""
        with patch("module.api.downloader.DownloadClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(
                return_value=mock_download_client
            )
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            response = authed_client.post(
                "/api/v1/downloader/torrents/pause",
                json={"hashes": ["abc123", "def456"]},
            )

        assert response.status_code == 200
        # Hashes are joined with |
        mock_download_client.pause_torrent.assert_called_once_with("abc123|def456")


# ---------------------------------------------------------------------------
# POST /downloader/torrents/resume
# ---------------------------------------------------------------------------


class TestResumeTorrents:
    def test_resume_single_torrent(self, authed_client, mock_download_client):
        """POST /downloader/torrents/resume resumes a single torrent."""
        with patch("module.api.downloader.DownloadClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(
                return_value=mock_download_client
            )
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            response = authed_client.post(
                "/api/v1/downloader/torrents/resume", json={"hashes": ["abc123"]}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["msg_en"] == "Torrents resumed"
        mock_download_client.resume_torrent.assert_called_once_with("abc123")

    def test_resume_multiple_torrents(self, authed_client, mock_download_client):
        """POST /downloader/torrents/resume resumes multiple torrents."""
        with patch("module.api.downloader.DownloadClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(
                return_value=mock_download_client
            )
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            response = authed_client.post(
                "/api/v1/downloader/torrents/resume",
                json={"hashes": ["abc123", "def456"]},
            )

        assert response.status_code == 200
        mock_download_client.resume_torrent.assert_called_once_with("abc123|def456")


# ---------------------------------------------------------------------------
# POST /downloader/torrents/delete
# ---------------------------------------------------------------------------


class TestDeleteTorrents:
    def test_delete_single_torrent_keep_files(
        self, authed_client, mock_download_client
    ):
        """POST /downloader/torrents/delete deletes torrent, keeps files."""
        with patch("module.api.downloader.DownloadClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(
                return_value=mock_download_client
            )
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            response = authed_client.post(
                "/api/v1/downloader/torrents/delete",
                json={"hashes": ["abc123"], "delete_files": False},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["msg_en"] == "Torrents deleted"
        mock_download_client.delete_torrent.assert_called_once_with(
            "abc123", delete_files=False
        )

    def test_delete_torrent_with_files(self, authed_client, mock_download_client):
        """POST /downloader/torrents/delete deletes torrent and files."""
        with patch("module.api.downloader.DownloadClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(
                return_value=mock_download_client
            )
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            response = authed_client.post(
                "/api/v1/downloader/torrents/delete",
                json={"hashes": ["abc123"], "delete_files": True},
            )

        assert response.status_code == 200
        mock_download_client.delete_torrent.assert_called_once_with(
            "abc123", delete_files=True
        )

    def test_delete_multiple_torrents(self, authed_client, mock_download_client):
        """POST /downloader/torrents/delete deletes multiple torrents."""
        with patch("module.api.downloader.DownloadClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(
                return_value=mock_download_client
            )
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            response = authed_client.post(
                "/api/v1/downloader/torrents/delete",
                json={"hashes": ["abc123", "def456"], "delete_files": False},
            )

        assert response.status_code == 200
        mock_download_client.delete_torrent.assert_called_once_with(
            "abc123|def456", delete_files=False
        )
