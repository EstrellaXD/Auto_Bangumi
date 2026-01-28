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


# ---------------------------------------------------------------------------
# POST /downloader/torrents/tag
# ---------------------------------------------------------------------------


class TestTagTorrent:
    def test_tag_torrent_success(self, authed_client, mock_download_client):
        """POST /downloader/torrents/tag adds bangumi tag to torrent."""
        from module.models import Bangumi

        mock_bangumi = Bangumi(
            id=123,
            official_title="Test Anime",
            title_raw="Test",
            season=1,
            rss_link="",
            poster_link="",
            added=False,
            deleted=False,
        )

        with patch("module.api.downloader.DownloadClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(
                return_value=mock_download_client
            )
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("module.api.downloader.Database") as MockDB:
                mock_db = MockDB.return_value.__enter__.return_value
                mock_db.bangumi.search_id.return_value = mock_bangumi

                response = authed_client.post(
                    "/api/v1/downloader/torrents/tag",
                    json={"hash": "abc123", "bangumi_id": 123},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert "ab:123" in data["msg_en"]
        mock_download_client.add_tag.assert_called_once_with("abc123", "ab:123")

    def test_tag_torrent_bangumi_not_found(self, authed_client, mock_download_client):
        """POST /downloader/torrents/tag fails if bangumi doesn't exist."""
        with patch("module.api.downloader.Database") as MockDB:
            mock_db = MockDB.return_value.__enter__.return_value
            mock_db.bangumi.search_id.return_value = None

            response = authed_client.post(
                "/api/v1/downloader/torrents/tag",
                json={"hash": "abc123", "bangumi_id": 999},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] is False
        assert "not found" in data["msg_en"]


# ---------------------------------------------------------------------------
# POST /downloader/torrents/tag/auto
# ---------------------------------------------------------------------------


class TestAutoTagTorrents:
    def test_auto_tag_success(self, authed_client, mock_download_client):
        """POST /downloader/torrents/tag/auto tags untagged torrents."""
        from module.models import Bangumi

        mock_bangumi = Bangumi(
            id=123,
            official_title="Test Anime",
            title_raw="Test Anime",
            season=1,
            rss_link="",
            poster_link="",
            added=False,
            deleted=False,
        )

        # Mock torrents - one untagged, one already tagged
        mock_download_client.get_torrent_info.return_value = [
            {
                "hash": "abc123",
                "name": "[TestGroup] Test Anime - 01.mkv",
                "save_path": "/downloads/Test Anime/Season 1",
                "tags": "",
            },
            {
                "hash": "def456",
                "name": "[TestGroup] Other Anime - 01.mkv",
                "save_path": "/downloads/Other Anime/Season 1",
                "tags": "ab:456",  # Already tagged
            },
        ]

        with patch("module.api.downloader.DownloadClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(
                return_value=mock_download_client
            )
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("module.api.downloader.Database") as MockDB:
                mock_db = MockDB.return_value.__enter__.return_value
                mock_db.bangumi.match_torrent.return_value = mock_bangumi
                mock_db.bangumi.match_by_save_path.return_value = None

                response = authed_client.post("/api/v1/downloader/torrents/tag/auto")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert data["tagged_count"] == 1
        # Only the untagged torrent should be tagged
        mock_download_client.add_tag.assert_called_once_with("abc123", "ab:123")

    def test_auto_tag_no_matches(self, authed_client, mock_download_client):
        """POST /downloader/torrents/tag/auto handles unmatched torrents."""
        mock_download_client.get_torrent_info.return_value = [
            {
                "hash": "abc123",
                "name": "[TestGroup] Unknown Anime - 01.mkv",
                "save_path": "/downloads/Unknown/Season 1",
                "tags": "",
            },
        ]

        with patch("module.api.downloader.DownloadClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(
                return_value=mock_download_client
            )
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("module.api.downloader.Database") as MockDB:
                mock_db = MockDB.return_value.__enter__.return_value
                mock_db.bangumi.match_torrent.return_value = None
                mock_db.bangumi.match_by_save_path.return_value = None

                response = authed_client.post("/api/v1/downloader/torrents/tag/auto")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert data["tagged_count"] == 0
        assert data["unmatched_count"] == 1
        assert len(data["unmatched"]) == 1
        mock_download_client.add_tag.assert_not_called()
