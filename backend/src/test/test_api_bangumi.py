"""Tests for Bangumi API endpoints."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from module.api import v1
from module.models import Bangumi, BangumiUpdate, ResponseModel
from module.security.api import get_current_user, active_user
from module.security.jwt import create_access_token

from test.factories import make_bangumi


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


# ---------------------------------------------------------------------------
# Auth requirement
# ---------------------------------------------------------------------------


class TestAuthRequired:
    def test_get_all_unauthorized(self, unauthed_client):
        """GET /bangumi/get/all without auth returns 401."""
        response = unauthed_client.get("/api/v1/bangumi/get/all")
        assert response.status_code == 401

    def test_get_by_id_unauthorized(self, unauthed_client):
        """GET /bangumi/get/1 without auth returns 401."""
        response = unauthed_client.get("/api/v1/bangumi/get/1")
        assert response.status_code == 401

    def test_delete_unauthorized(self, unauthed_client):
        """DELETE /bangumi/delete/1 without auth returns 401."""
        response = unauthed_client.delete("/api/v1/bangumi/delete/1")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET endpoints
# ---------------------------------------------------------------------------


class TestGetBangumi:
    def test_get_all(self, authed_client):
        """GET /bangumi/get/all returns list of Bangumi."""
        mock_bangumi = [make_bangumi(id=1), make_bangumi(id=2, title_raw="Other")]
        with patch("module.api.bangumi.TorrentManager") as MockManager:
            mock_mgr = MagicMock()
            mock_mgr.bangumi.search_all.return_value = mock_bangumi
            MockManager.return_value.__enter__ = MagicMock(return_value=mock_mgr)
            MockManager.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.get("/api/v1/bangumi/get/all")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_by_id(self, authed_client):
        """GET /bangumi/get/{id} returns single Bangumi."""
        bangumi = make_bangumi(id=1, official_title="Found Anime")
        with patch("module.api.bangumi.TorrentManager") as MockManager:
            mock_mgr = MagicMock()
            mock_mgr.search_one.return_value = bangumi
            MockManager.return_value.__enter__ = MagicMock(return_value=mock_mgr)
            MockManager.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.get("/api/v1/bangumi/get/1")

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# PATCH/UPDATE endpoints
# ---------------------------------------------------------------------------


class TestUpdateBangumi:
    def test_update_success(self, authed_client):
        """PATCH /bangumi/update/{id} updates and returns success."""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Updated.", msg_zh="已更新。"
        )
        with patch("module.api.bangumi.TorrentManager") as MockManager:
            mock_mgr = MagicMock()
            mock_mgr.update_rule = AsyncMock(return_value=resp_model)
            MockManager.return_value.__enter__ = MagicMock(return_value=mock_mgr)
            MockManager.return_value.__exit__ = MagicMock(return_value=False)

            # BangumiUpdate requires all fields
            update_data = {
                "official_title": "New Title",
                "title_raw": "new_raw",
                "season": 1,
                "year": "2024",
                "season_raw": "",
                "group_name": "Group",
                "dpi": "1080p",
                "source": "Web",
                "subtitle": "CHT",
                "eps_collect": False,
                "offset": 0,
                "filter": "720",
                "rss_link": "https://test.com/rss",
                "poster_link": None,
                "added": True,
                "rule_name": None,
                "save_path": None,
                "deleted": False,
            }
            response = authed_client.patch(
                "/api/v1/bangumi/update/1",
                json=update_data,
            )

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# DELETE endpoints
# ---------------------------------------------------------------------------


class TestDeleteBangumi:
    def test_delete_success(self, authed_client):
        """DELETE /bangumi/delete/{id} removes bangumi."""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Deleted.", msg_zh="已删除。"
        )
        with patch("module.api.bangumi.TorrentManager") as MockManager:
            mock_mgr = MagicMock()
            mock_mgr.delete_rule = AsyncMock(return_value=resp_model)
            MockManager.return_value.__enter__ = MagicMock(return_value=mock_mgr)
            MockManager.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.delete("/api/v1/bangumi/delete/1")

        assert response.status_code == 200

    def test_disable_rule(self, authed_client):
        """DELETE /bangumi/disable/{id} marks as deleted."""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Disabled.", msg_zh="已禁用。"
        )
        with patch("module.api.bangumi.TorrentManager") as MockManager:
            mock_mgr = MagicMock()
            mock_mgr.disable_rule = AsyncMock(return_value=resp_model)
            MockManager.return_value.__enter__ = MagicMock(return_value=mock_mgr)
            MockManager.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.delete("/api/v1/bangumi/disable/1")

        assert response.status_code == 200

    def test_enable_rule(self, authed_client):
        """GET /bangumi/enable/{id} re-enables rule."""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Enabled.", msg_zh="已启用。"
        )
        with patch("module.api.bangumi.TorrentManager") as MockManager:
            mock_mgr = MagicMock()
            mock_mgr.enable_rule.return_value = resp_model
            MockManager.return_value.__enter__ = MagicMock(return_value=mock_mgr)
            MockManager.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.get("/api/v1/bangumi/enable/1")

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


class TestResetBangumi:
    def test_reset_all(self, authed_client):
        """GET /bangumi/reset/all deletes all bangumi."""
        with patch("module.api.bangumi.TorrentManager") as MockManager:
            mock_mgr = MagicMock()
            mock_mgr.bangumi.delete_all.return_value = None
            MockManager.return_value.__enter__ = MagicMock(return_value=mock_mgr)
            MockManager.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.get("/api/v1/bangumi/reset/all")

        assert response.status_code == 200
