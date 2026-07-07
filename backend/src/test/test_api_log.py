"""Tests for Log API endpoints."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
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
        """POST /log/clear without auth returns 401."""
        response = unauthed_client.post("/api/v1/log/clear")
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

    def test_get_log_stitches_rotated_backup(self, authed_client, temp_log_file):
        """轮转刚发生后 log.txt 很小：把 log.txt.1 的尾部拼在前面，
        UI 不出现"日志突然清空"的断崖。"""
        backup = temp_log_file.with_name(temp_log_file.name + ".1")
        backup.write_text("2024-01-01 11:59:59 INFO Rotated entry\n")
        temp_log_file.write_text("2024-01-01 12:00:00 INFO Current entry\n")

        with patch("module.api.log.LOG_PATH", temp_log_file):
            response = authed_client.get("/api/v1/log")

        assert response.status_code == 200
        assert response.text.index("Rotated entry") < response.text.index(
            "Current entry"
        )

    def test_get_log_truncated_current_file_skips_backup(
        self, authed_client, temp_log_file
    ):
        """当前文件本身超出预算（被截断读取）时绝不拼接备份：中间内容
        已经缺失，再把更旧的备份贴在上面会造成时间倒跳的假象。"""
        backup = temp_log_file.with_name(temp_log_file.name + ".1")
        # 故意不带结尾换行：拼接判断若有误，备份内容必然泄漏进响应
        backup.write_text("OLD backup line without newline")
        temp_log_file.write_text("padding line\n" * 10 + "CURRENT tail line\n")

        with (
            patch("module.api.log.LOG_PATH", temp_log_file),
            patch("module.api.log._TAIL_BYTES", 64),
        ):
            response = authed_client.get("/api/v1/log")

        assert response.status_code == 200
        assert "CURRENT tail line" in response.text
        assert "OLD backup" not in response.text

    def test_read_file_tail_missing_file_is_empty(self, temp_log_file):
        """轮转竞态：exists() 之后文件被改名——按空文件处理而非抛异常
        （异常会炸掉 GET /log 和整条 SSE 流）。"""
        from module.api.log import _read_file_tail

        missing = temp_log_file.with_name("gone.txt")
        assert _read_file_tail(missing, 100) == (b"", False)


# ---------------------------------------------------------------------------
# POST /log/clear
# ---------------------------------------------------------------------------


class TestClearLog:
    def test_clear_log_success(self, authed_client, temp_log_file):
        """POST /log/clear clears the log file."""
        # Ensure file has content
        temp_log_file.write_text("Some log content")
        assert temp_log_file.read_text() != ""

        with patch("module.api.log.LOG_PATH", temp_log_file):
            response = authed_client.post("/api/v1/log/clear")

        assert response.status_code == 200
        data = response.json()
        assert data["msg_en"] == "Log cleared successfully."
        assert temp_log_file.read_text() == ""

    def test_clear_log_removes_rotated_backups(self, authed_client, temp_log_file):
        """清空日志时同时删除轮转备份，否则拼接读取会把旧内容带回来。"""
        backup1 = temp_log_file.with_name(temp_log_file.name + ".1")
        backup2 = temp_log_file.with_name(temp_log_file.name + ".2")
        backup1.write_text("old 1")
        backup2.write_text("old 2")

        with patch("module.api.log.LOG_PATH", temp_log_file):
            response = authed_client.post("/api/v1/log/clear")

        assert response.status_code == 200
        assert not backup1.exists()
        assert not backup2.exists()

    def test_clear_log_not_found(self, authed_client):
        """POST /log/clear returns 404 when log file doesn't exist."""
        non_existent_path = Path("/nonexistent/path/app.log")
        with patch("module.api.log.LOG_PATH", non_existent_path):
            response = authed_client.post("/api/v1/log/clear")

        assert response.status_code == 404
        data = response.json()
        assert data["msg_en"] == "Log file not found."
