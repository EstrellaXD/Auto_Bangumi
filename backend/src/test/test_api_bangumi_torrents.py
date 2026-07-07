"""Tests for Bangumi torrent-management API endpoints (#1020 port)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from module.api import v1
from module.database import get_db
from module.models import Torrent
from module.security.api import get_current_user

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db():
    """A stand-in Database whose repos can be configured with AsyncMocks."""
    return MagicMock()


@pytest.fixture
def app(mock_db):
    """Create a FastAPI app with v1 routes for testing."""
    app = FastAPI()
    app.include_router(v1, prefix="/api")

    async def _override_get_db():
        yield mock_db

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


def _torrent(_id: int, bangumi_id: int | None) -> Torrent:
    return Torrent(
        id=_id,
        name=f"torrent_{_id}",
        url=f"https://example.com/{_id}",
        bangumi_id=bangumi_id,
    )


# ---------------------------------------------------------------------------
# Auth requirement
# ---------------------------------------------------------------------------


class TestAuthRequired:
    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_get_orphans_unauthorized(self, unauthed_client):
        """GET /bangumi/torrents/orphans without auth returns 401."""
        response = unauthed_client.get("/api/v1/bangumi/torrents/orphans")
        assert response.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_delete_orphans_unauthorized(self, unauthed_client):
        """DELETE /bangumi/torrents/orphans without auth returns 401."""
        response = unauthed_client.delete("/api/v1/bangumi/torrents/orphans")
        assert response.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_get_bangumi_torrents_unauthorized(self, unauthed_client):
        """GET /bangumi/1/torrents without auth returns 401."""
        response = unauthed_client.get("/api/v1/bangumi/1/torrents")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Orphan torrents
# ---------------------------------------------------------------------------


class TestOrphanTorrents:
    def test_get_orphans_returns_list(self, authed_client, mock_db):
        """GET /bangumi/torrents/orphans returns orphan torrent list."""
        mock_db.torrent.search_orphans = AsyncMock(
            return_value=[_torrent(1, None), _torrent(2, None)]
        )
        response = authed_client.get("/api/v1/bangumi/torrents/orphans")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "torrent_1"

    def test_get_orphan_count(self, authed_client, mock_db):
        """GET /bangumi/torrents/orphans/count returns the count."""
        mock_db.torrent.count_orphans = AsyncMock(return_value=3)
        response = authed_client.get("/api/v1/bangumi/torrents/orphans/count")
        assert response.status_code == 200
        assert response.json() == 3

    def test_delete_orphans_returns_count_message(self, authed_client, mock_db):
        """DELETE /bangumi/torrents/orphans deletes all orphans."""
        mock_db.torrent.delete_orphans = AsyncMock(return_value=2)
        response = authed_client.delete("/api/v1/bangumi/torrents/orphans")
        assert response.status_code == 200
        assert "2" in response.json()["msg_en"]
        mock_db.torrent.delete_orphans.assert_awaited_once()

    def test_delete_single_orphan(self, authed_client, mock_db):
        """DELETE /bangumi/torrents/orphans/{id} deletes one orphan."""
        mock_db.torrent.search = AsyncMock(return_value=_torrent(5, None))
        mock_db.torrent.delete_obj = AsyncMock()
        response = authed_client.delete("/api/v1/bangumi/torrents/orphans/5")
        assert response.status_code == 200
        mock_db.torrent.delete_obj.assert_awaited_once()

    def test_delete_single_orphan_not_found(self, authed_client, mock_db):
        """DELETE /bangumi/torrents/orphans/{id} returns 404 for missing torrent."""
        mock_db.torrent.search = AsyncMock(return_value=None)
        response = authed_client.delete("/api/v1/bangumi/torrents/orphans/99")
        assert response.status_code == 404

    def test_delete_single_orphan_rejects_matched_torrent(self, authed_client, mock_db):
        """DELETE /bangumi/torrents/orphans/{id} returns 404 if torrent has a bangumi."""
        mock_db.torrent.search = AsyncMock(return_value=_torrent(5, bangumi_id=1))
        mock_db.torrent.delete_obj = AsyncMock()
        response = authed_client.delete("/api/v1/bangumi/torrents/orphans/5")
        assert response.status_code == 404
        mock_db.torrent.delete_obj.assert_not_awaited()


# ---------------------------------------------------------------------------
# Per-bangumi torrents
# ---------------------------------------------------------------------------


class TestBangumiTorrents:
    def test_get_bangumi_torrents(self, authed_client, mock_db):
        """GET /bangumi/{id}/torrents returns that bangumi's torrents."""
        mock_db.torrent.search_by_bangumi_id = AsyncMock(return_value=[_torrent(1, 7)])
        response = authed_client.get("/api/v1/bangumi/7/torrents")
        assert response.status_code == 200
        assert len(response.json()) == 1
        mock_db.torrent.search_by_bangumi_id.assert_awaited_once_with(7)

    def test_delete_bangumi_torrents(self, authed_client, mock_db):
        """DELETE /bangumi/{id}/torrents deletes all torrents of a bangumi."""
        mock_db.torrent.delete_by_bangumi_id = AsyncMock(return_value=4)
        response = authed_client.delete("/api/v1/bangumi/7/torrents")
        assert response.status_code == 200
        assert "4" in response.json()["msg_en"]
        mock_db.torrent.delete_by_bangumi_id.assert_awaited_once_with(7)

    def test_delete_single_torrent(self, authed_client, mock_db):
        """DELETE /bangumi/{id}/torrents/{tid} deletes one torrent."""
        mock_db.torrent.search = AsyncMock(return_value=_torrent(3, 7))
        mock_db.torrent.delete_obj = AsyncMock()
        response = authed_client.delete("/api/v1/bangumi/7/torrents/3")
        assert response.status_code == 200
        mock_db.torrent.delete_obj.assert_awaited_once()

    def test_delete_single_torrent_wrong_bangumi(self, authed_client, mock_db):
        """DELETE /bangumi/{id}/torrents/{tid} returns 404 if owner mismatches."""
        mock_db.torrent.search = AsyncMock(return_value=_torrent(3, 8))
        mock_db.torrent.delete_obj = AsyncMock()
        response = authed_client.delete("/api/v1/bangumi/7/torrents/3")
        assert response.status_code == 404
        mock_db.torrent.delete_obj.assert_not_awaited()

    def test_delete_single_torrent_not_found(self, authed_client, mock_db):
        """DELETE /bangumi/{id}/torrents/{tid} returns 404 for missing torrent."""
        mock_db.torrent.search = AsyncMock(return_value=None)
        response = authed_client.delete("/api/v1/bangumi/7/torrents/99")
        assert response.status_code == 404
