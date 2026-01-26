"""Tests for Log API endpoints."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

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
def temp_log_file():
    """Create a temporary log file for testing."""
    with TemporaryDirectory() as temp_dir:
        log_path = Path(temp_dir) / "app.log"
        log_path.write_text("2024-01-01 12:00:00 INFO Test log entry\n")
        yield log_path


# ---------------------------------------------------------------------------
# Auth requirement
# ---------------------------------------------------------------------------


class TestAuthRequired:
    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_get_log_unauthorized(self, unauthed_client):
        """GET /log without auth returns 401."""
        response = unauthed_client.get("/api/v1/log")
        assert response.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_clear_log_unauthorized(self, unauthed_client):
        """GET /log/clear without auth returns 401."""
        response = unauthed_client.get("/api/v1/log/clear")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /log
# ---------------------------------------------------------------------------


class TestGetLog:
    def test_get_log_success(self, authed_client, temp_log_file):
        """GET /log returns log content."""
        with patch("module.api.log.LOG_PATH", temp_log_file):
            response = authed_client.get("/api/v1/log")

        assert response.status_code == 200
        assert "Test log entry" in response.text

    def test_get_log_not_found(self, authed_client):
        """GET /log returns 404 when log file doesn't exist."""
        non_existent_path = Path("/nonexistent/path/app.log")
        with patch("module.api.log.LOG_PATH", non_existent_path):
            response = authed_client.get("/api/v1/log")

        assert response.status_code == 404

    def test_get_log_multiline(self, authed_client, temp_log_file):
        """GET /log returns multiple log lines."""
        temp_log_file.write_text(
            "2024-01-01 12:00:00 INFO First entry\n"
            "2024-01-01 12:00:01 WARNING Second entry\n"
            "2024-01-01 12:00:02 ERROR Third entry\n"
        )
        with patch("module.api.log.LOG_PATH", temp_log_file):
            response = authed_client.get("/api/v1/log")

        assert response.status_code == 200
        assert "First entry" in response.text
        assert "Second entry" in response.text
        assert "Third entry" in response.text


# ---------------------------------------------------------------------------
# GET /log/clear
# ---------------------------------------------------------------------------


class TestClearLog:
    def test_clear_log_success(self, authed_client, temp_log_file):
        """GET /log/clear clears the log file."""
        # Ensure file has content
        temp_log_file.write_text("Some log content")
        assert temp_log_file.read_text() != ""

        with patch("module.api.log.LOG_PATH", temp_log_file):
            response = authed_client.get("/api/v1/log/clear")

        assert response.status_code == 200
        data = response.json()
        assert data["msg_en"] == "Log cleared successfully."
        assert temp_log_file.read_text() == ""

    def test_clear_log_not_found(self, authed_client):
        """GET /log/clear returns 406 when log file doesn't exist."""
        non_existent_path = Path("/nonexistent/path/app.log")
        with patch("module.api.log.LOG_PATH", non_existent_path):
            response = authed_client.get("/api/v1/log/clear")

        assert response.status_code == 406
        data = response.json()
        assert data["msg_en"] == "Log file not found."
