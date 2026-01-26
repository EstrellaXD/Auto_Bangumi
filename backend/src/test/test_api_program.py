"""Tests for Program API endpoints."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from module.api import v1
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
def mock_program():
    """Mock Program instance."""
    program = MagicMock()
    program.is_running = True
    program.first_run = False
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
# Auth requirement
# ---------------------------------------------------------------------------


class TestAuthRequired:
    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_restart_unauthorized(self, unauthed_client):
        """GET /restart without auth returns 401."""
        response = unauthed_client.get("/api/v1/restart")
        assert response.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_start_unauthorized(self, unauthed_client):
        """GET /start without auth returns 401."""
        response = unauthed_client.get("/api/v1/start")
        assert response.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_stop_unauthorized(self, unauthed_client):
        """GET /stop without auth returns 401."""
        response = unauthed_client.get("/api/v1/stop")
        assert response.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_status_unauthorized(self, unauthed_client):
        """GET /status without auth returns 401."""
        response = unauthed_client.get("/api/v1/status")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /start
# ---------------------------------------------------------------------------


class TestStartProgram:
    def test_start_success(self, authed_client, mock_program):
        """GET /start returns success response."""
        with patch("module.api.program.program", mock_program):
            response = authed_client.get("/api/v1/start")

        assert response.status_code == 200

    def test_start_failure(self, authed_client, mock_program):
        """GET /start handles exceptions."""
        mock_program.start = AsyncMock(side_effect=Exception("Start failed"))
        with patch("module.api.program.program", mock_program):
            response = authed_client.get("/api/v1/start")

        assert response.status_code == 500


# ---------------------------------------------------------------------------
# GET /stop
# ---------------------------------------------------------------------------


class TestStopProgram:
    def test_stop_success(self, authed_client, mock_program):
        """GET /stop returns success response."""
        with patch("module.api.program.program", mock_program):
            response = authed_client.get("/api/v1/stop")

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /restart
# ---------------------------------------------------------------------------


class TestRestartProgram:
    def test_restart_success(self, authed_client, mock_program):
        """GET /restart returns success response."""
        with patch("module.api.program.program", mock_program):
            response = authed_client.get("/api/v1/restart")

        assert response.status_code == 200

    def test_restart_failure(self, authed_client, mock_program):
        """GET /restart handles exceptions."""
        mock_program.restart = AsyncMock(side_effect=Exception("Restart failed"))
        with patch("module.api.program.program", mock_program):
            response = authed_client.get("/api/v1/restart")

        assert response.status_code == 500


# ---------------------------------------------------------------------------
# GET /status
# ---------------------------------------------------------------------------


class TestProgramStatus:
    def test_status_running(self, authed_client, mock_program):
        """GET /status returns running status."""
        mock_program.is_running = True
        mock_program.first_run = False
        with patch("module.api.program.program", mock_program):
            with patch("module.api.program.VERSION", "3.2.0"):
                response = authed_client.get("/api/v1/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        assert data["version"] == "3.2.0"
        assert data["first_run"] is False

    def test_status_stopped(self, authed_client, mock_program):
        """GET /status returns stopped status."""
        mock_program.is_running = False
        mock_program.first_run = True
        with patch("module.api.program.program", mock_program):
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
    def test_check_downloader_connected(self, authed_client, mock_program):
        """GET /check/downloader returns True when connected."""
        mock_program.check_downloader = AsyncMock(return_value=True)
        with patch("module.api.program.program", mock_program):
            response = authed_client.get("/api/v1/check/downloader")

        assert response.status_code == 200
        assert response.json() is True

    def test_check_downloader_disconnected(self, authed_client, mock_program):
        """GET /check/downloader returns False when disconnected."""
        mock_program.check_downloader = AsyncMock(return_value=False)
        with patch("module.api.program.program", mock_program):
            response = authed_client.get("/api/v1/check/downloader")

        assert response.status_code == 200
        assert response.json() is False
