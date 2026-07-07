"""Tests for Program API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from module.api import v1
from module.api.deps import get_context
from module.models import ResponseModel
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
def mock_ctx():
    """Mock AppContext instance injected via the get_context dependency."""
    ctx = MagicMock()
    ctx.is_running = True
    ctx.first_run = False
    ctx.start_tasks = AsyncMock(
        return_value=ResponseModel(
            status=True, status_code=200, msg_en="Started.", msg_zh="已启动。"
        )
    )
    ctx.stop = AsyncMock(
        return_value=ResponseModel(
            status=True, status_code=200, msg_en="Stopped.", msg_zh="已停止。"
        )
    )
    ctx.restart = AsyncMock(
        return_value=ResponseModel(
            status=True, status_code=200, msg_en="Restarted.", msg_zh="已重启。"
        )
    )
    ctx.check_downloader = AsyncMock(return_value=True)
    return ctx


@pytest.fixture
def authed_client(app, mock_ctx):
    """TestClient with auth and context dependencies overridden."""

    async def mock_user():
        return "testuser"

    app.dependency_overrides[get_current_user] = mock_user
    app.dependency_overrides[get_context] = lambda: mock_ctx
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
    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_restart_unauthorized(self, unauthed_client):
        """POST /restart without auth returns 401."""
        response = unauthed_client.post("/api/v1/restart")
        assert response.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_start_unauthorized(self, unauthed_client):
        """POST /start without auth returns 401."""
        response = unauthed_client.post("/api/v1/start")
        assert response.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_stop_unauthorized(self, unauthed_client):
        """POST /stop without auth returns 401."""
        response = unauthed_client.post("/api/v1/stop")
        assert response.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_status_unauthorized(self, unauthed_client):
        """GET /status without auth returns 401."""
        response = unauthed_client.get("/api/v1/status")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /start
# ---------------------------------------------------------------------------


class TestStartProgram:
    def test_start_success(self, authed_client):
        """POST /start returns success response."""
        response = authed_client.post("/api/v1/start")
        assert response.status_code == 200

    def test_start_failure(self, authed_client, mock_ctx):
        """POST /start handles exceptions."""
        mock_ctx.start_tasks = AsyncMock(side_effect=Exception("Start failed"))
        response = authed_client.post("/api/v1/start")
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# POST /stop
# ---------------------------------------------------------------------------


class TestStopProgram:
    def test_stop_success(self, authed_client):
        """POST /stop returns success response."""
        response = authed_client.post("/api/v1/stop")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /restart
# ---------------------------------------------------------------------------


class TestRestartProgram:
    def test_restart_success(self, authed_client):
        """POST /restart returns success response."""
        response = authed_client.post("/api/v1/restart")
        assert response.status_code == 200

    def test_restart_failure(self, authed_client, mock_ctx):
        """POST /restart handles exceptions."""
        mock_ctx.restart = AsyncMock(side_effect=Exception("Restart failed"))
        response = authed_client.post("/api/v1/restart")
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# 3.2 GET compatibility shims
# ---------------------------------------------------------------------------


class TestLegacyGetCompat:
    """3.2 及更早版本的控制端点是 GET；外部自动化（cron/Home Assistant）
    升级到 3.3 后不得 405 静默失效。"""

    def test_restart_get_compat(self, authed_client):
        assert authed_client.get("/api/v1/restart").status_code == 200

    def test_start_get_compat(self, authed_client):
        assert authed_client.get("/api/v1/start").status_code == 200

    def test_stop_get_compat(self, authed_client):
        assert authed_client.get("/api/v1/stop").status_code == 200

    def test_shutdown_get_route_exists(self, unauthed_client):
        # 不真调用（会杀掉测试进程）：无鉴权应得 401，说明路由存在；
        # 不存在的方法是 405。
        assert unauthed_client.get("/api/v1/shutdown").status_code == 401


# ---------------------------------------------------------------------------
# GET /status
# ---------------------------------------------------------------------------


class TestProgramStatus:
    def test_status_running(self, authed_client, mock_ctx):
        """GET /status returns running status."""
        mock_ctx.is_running = True
        mock_ctx.first_run = False
        with patch("module.api.program.VERSION", "3.2.0"):
            response = authed_client.get("/api/v1/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert data["version"] == "3.2.0"
        assert data["first_run"] is False

    def test_status_stopped(self, authed_client, mock_ctx):
        """GET /status returns stopped status."""
        mock_ctx.is_running = False
        mock_ctx.first_run = True
        with patch("module.api.program.VERSION", "3.2.0"):
            response = authed_client.get("/api/v1/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] is False
        assert data["first_run"] is True


# ---------------------------------------------------------------------------
# GET /check/downloader
# ---------------------------------------------------------------------------


class TestCheckDownloader:
    def test_check_downloader_connected(self, authed_client, mock_ctx):
        """GET /check/downloader returns True when connected."""
        mock_ctx.check_downloader = AsyncMock(return_value=True)
        response = authed_client.get("/api/v1/check/downloader")

        assert response.status_code == 200
        assert response.json() is True

    def test_check_downloader_disconnected(self, authed_client, mock_ctx):
        """GET /check/downloader returns False when disconnected."""
        mock_ctx.check_downloader = AsyncMock(return_value=False)
        response = authed_client.get("/api/v1/check/downloader")

        assert response.status_code == 200
        assert response.json() is False
