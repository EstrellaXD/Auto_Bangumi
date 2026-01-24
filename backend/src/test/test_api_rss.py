"""Tests for RSS API endpoints."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from module.api import v1
from module.models import RSSItem, RSSUpdate, ResponseModel, Torrent
from module.security.api import get_current_user

from test.factories import make_rss_item, make_torrent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(v1, prefix="/api")
    return app


@pytest.fixture
def authed_client(app):
    async def mock_user():
        return "testuser"

    app.dependency_overrides[get_current_user] = mock_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def unauthed_client(app):
    return TestClient(app)


# ---------------------------------------------------------------------------
# Auth requirement
# ---------------------------------------------------------------------------


class TestAuthRequired:
    def test_get_rss_unauthorized(self, unauthed_client):
        """GET /rss without auth returns 401."""
        response = unauthed_client.get("/api/v1/rss")
        assert response.status_code == 401

    def test_add_rss_unauthorized(self, unauthed_client):
        """POST /rss/add without auth returns 401."""
        response = unauthed_client.post(
            "/api/v1/rss/add", json={"url": "https://test.com"}
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /rss
# ---------------------------------------------------------------------------


class TestGetRss:
    def test_get_all(self, authed_client):
        """GET /rss returns list of RSSItems."""
        items = [
            make_rss_item(id=1, name="Feed 1"),
            make_rss_item(id=2, name="Feed 2"),
        ]
        with patch("module.api.rss.RSSEngine") as MockEngine:
            mock_eng = MagicMock()
            mock_eng.rss.search_all.return_value = items
            MockEngine.return_value.__enter__ = MagicMock(return_value=mock_eng)
            MockEngine.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.get("/api/v1/rss")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


# ---------------------------------------------------------------------------
# POST /rss/add
# ---------------------------------------------------------------------------


class TestAddRss:
    def test_add_success(self, authed_client):
        """POST /rss/add creates a new RSS feed."""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Added.", msg_zh="添加成功。"
        )
        with patch("module.api.rss.RSSEngine") as MockEngine:
            mock_eng = MagicMock()
            mock_eng.add_rss = AsyncMock(return_value=resp_model)
            MockEngine.return_value.__enter__ = MagicMock(return_value=mock_eng)
            MockEngine.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.post(
                "/api/v1/rss/add",
                json={
                    "url": "https://mikanani.me/RSS/test",
                    "name": "Test Feed",
                    "aggregate": True,
                    "parser": "mikan",
                },
            )

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# DELETE /rss/delete/{id}
# ---------------------------------------------------------------------------


class TestDeleteRss:
    def test_delete_success(self, authed_client):
        """DELETE /rss/delete/{id} removes the feed."""
        with patch("module.api.rss.RSSEngine") as MockEngine:
            mock_eng = MagicMock()
            mock_eng.rss.delete.return_value = True
            MockEngine.return_value.__enter__ = MagicMock(return_value=mock_eng)
            MockEngine.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.delete("/api/v1/rss/delete/1")

        assert response.status_code == 200

    def test_delete_failure(self, authed_client):
        """DELETE /rss/delete/{id} returns 406 when feed not found."""
        with patch("module.api.rss.RSSEngine") as MockEngine:
            mock_eng = MagicMock()
            mock_eng.rss.delete.return_value = False
            MockEngine.return_value.__enter__ = MagicMock(return_value=mock_eng)
            MockEngine.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.delete("/api/v1/rss/delete/999")

        assert response.status_code == 406


# ---------------------------------------------------------------------------
# PATCH /rss/disable/{id}
# ---------------------------------------------------------------------------


class TestDisableRss:
    def test_disable_success(self, authed_client):
        """PATCH /rss/disable/{id} disables the feed."""
        with patch("module.api.rss.RSSEngine") as MockEngine:
            mock_eng = MagicMock()
            mock_eng.rss.disable.return_value = True
            MockEngine.return_value.__enter__ = MagicMock(return_value=mock_eng)
            MockEngine.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.patch("/api/v1/rss/disable/1")

        assert response.status_code == 200

    def test_disable_failure(self, authed_client):
        """PATCH /rss/disable/{id} returns 406 when feed not found."""
        with patch("module.api.rss.RSSEngine") as MockEngine:
            mock_eng = MagicMock()
            mock_eng.rss.disable.return_value = False
            MockEngine.return_value.__enter__ = MagicMock(return_value=mock_eng)
            MockEngine.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.patch("/api/v1/rss/disable/999")

        assert response.status_code == 406


# ---------------------------------------------------------------------------
# POST /rss/enable/many, /rss/disable/many, /rss/delete/many
# ---------------------------------------------------------------------------


class TestBatchOperations:
    def test_enable_many(self, authed_client):
        """POST /rss/enable/many enables multiple feeds."""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Enabled.", msg_zh="启用成功。"
        )
        with patch("module.api.rss.RSSEngine") as MockEngine:
            mock_eng = MagicMock()
            mock_eng.enable_list.return_value = resp_model
            MockEngine.return_value.__enter__ = MagicMock(return_value=mock_eng)
            MockEngine.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.post("/api/v1/rss/enable/many", json=[1, 2, 3])

        assert response.status_code == 200

    def test_disable_many(self, authed_client):
        """POST /rss/disable/many disables multiple feeds."""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Disabled.", msg_zh="禁用成功。"
        )
        with patch("module.api.rss.RSSEngine") as MockEngine:
            mock_eng = MagicMock()
            mock_eng.disable_list.return_value = resp_model
            MockEngine.return_value.__enter__ = MagicMock(return_value=mock_eng)
            MockEngine.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.post("/api/v1/rss/disable/many", json=[1, 2])

        assert response.status_code == 200

    def test_delete_many(self, authed_client):
        """POST /rss/delete/many deletes multiple feeds."""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Deleted.", msg_zh="删除成功。"
        )
        with patch("module.api.rss.RSSEngine") as MockEngine:
            mock_eng = MagicMock()
            mock_eng.delete_list.return_value = resp_model
            MockEngine.return_value.__enter__ = MagicMock(return_value=mock_eng)
            MockEngine.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.post("/api/v1/rss/delete/many", json=[1, 2])

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# PATCH /rss/update/{id}
# ---------------------------------------------------------------------------


class TestUpdateRss:
    def test_update_success(self, authed_client):
        """PATCH /rss/update/{id} updates feed."""
        with patch("module.api.rss.RSSEngine") as MockEngine:
            mock_eng = MagicMock()
            mock_eng.rss.update.return_value = True
            MockEngine.return_value.__enter__ = MagicMock(return_value=mock_eng)
            MockEngine.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.patch(
                "/api/v1/rss/update/1",
                json={"name": "Updated Name", "aggregate": False},
            )

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /rss/refresh/*
# ---------------------------------------------------------------------------


class TestRefreshRss:
    def test_refresh_all(self, authed_client):
        """GET /rss/refresh/all triggers engine.refresh_rss."""
        with patch("module.api.rss.DownloadClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("module.api.rss.RSSEngine") as MockEngine:
                mock_eng = MagicMock()
                mock_eng.refresh_rss = AsyncMock()
                MockEngine.return_value.__enter__ = MagicMock(return_value=mock_eng)
                MockEngine.return_value.__exit__ = MagicMock(return_value=False)

                response = authed_client.get("/api/v1/rss/refresh/all")

        assert response.status_code == 200

    def test_refresh_single(self, authed_client):
        """GET /rss/refresh/{id} refreshes specific feed."""
        with patch("module.api.rss.DownloadClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("module.api.rss.RSSEngine") as MockEngine:
                mock_eng = MagicMock()
                mock_eng.refresh_rss = AsyncMock()
                MockEngine.return_value.__enter__ = MagicMock(return_value=mock_eng)
                MockEngine.return_value.__exit__ = MagicMock(return_value=False)

                response = authed_client.get("/api/v1/rss/refresh/1")

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /rss/torrent/{id}
# ---------------------------------------------------------------------------


class TestGetRssTorrents:
    def test_get_torrents(self, authed_client):
        """GET /rss/torrent/{id} returns torrents for that feed."""
        torrents = [make_torrent(id=1, rss_id=1), make_torrent(id=2, rss_id=1)]
        with patch("module.api.rss.RSSEngine") as MockEngine:
            mock_eng = MagicMock()
            mock_eng.get_rss_torrents.return_value = torrents
            MockEngine.return_value.__enter__ = MagicMock(return_value=mock_eng)
            MockEngine.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.get("/api/v1/rss/torrent/1")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
