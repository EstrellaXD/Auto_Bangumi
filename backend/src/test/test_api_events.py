"""Tests for the events SSE endpoint and its payload builders."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from module.api import v1
from module.api.events import _downloader_payload, _log_payload, _status_payload

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
def unauthed_client(app):
    """TestClient without auth (no override)."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Auth requirement — safe to hit synchronously: the dependency rejects the
# request with 401 before the (otherwise-infinite) generator ever starts.
# ---------------------------------------------------------------------------


class TestAuthRequired:
    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_stream_unauthorized(self, unauthed_client):
        """GET /events/stream without auth returns 401."""
        response = unauthed_client.get("/api/v1/events/stream")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Payload builders — exercised directly (not through the infinite generator)
# ---------------------------------------------------------------------------


class TestStatusPayload:
    def test_status_payload_running(self):
        """_status_payload mirrors GET /program/status's running shape."""
        ctx = MagicMock()
        ctx.is_running = True
        ctx.first_run = False

        payload = _status_payload(ctx)

        assert payload["status"] is True
        assert payload["first_run"] is False
        assert "version" in payload

    def test_status_payload_stopped(self):
        """_status_payload reflects a stopped program."""
        ctx = MagicMock()
        ctx.is_running = False
        ctx.first_run = True

        payload = _status_payload(ctx)

        assert payload["status"] is False
        assert payload["first_run"] is True


class TestDownloaderPayload:
    async def test_downloader_payload_success(self):
        """_downloader_payload returns the torrent list on success."""
        torrents = [{"hash": "abc", "name": "Episode 1"}]
        mock_client = AsyncMock()
        mock_client.get_torrent_info = AsyncMock(return_value=torrents)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("module.api.events.DownloadClient", return_value=mock_client):
            result = await _downloader_payload()

        assert result == torrents
        mock_client.get_torrent_info.assert_called_once_with(
            category="Bangumi", status_filter=None
        )

    async def test_downloader_payload_unavailable_returns_none(self):
        """_downloader_payload swallows client errors and returns None so the
        stream skips that tick instead of crashing the connection."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(side_effect=RuntimeError("no downloader"))
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("module.api.events.DownloadClient", return_value=mock_client):
            result = await _downloader_payload()

        assert result is None


class TestLogPayload:
    async def test_log_payload_missing_file_returns_none(self, tmp_path):
        """_log_payload returns None when the log file doesn't exist yet."""
        missing = tmp_path / "does-not-exist.log"
        with patch("module.api.events.LOG_PATH", missing):
            result = await _log_payload()

        assert result is None

    async def test_log_payload_reads_tail(self, tmp_path):
        """_log_payload decodes the tail bytes read via _read_log_tail.

        _read_log_tail (imported from module.api.log) resolves LOG_PATH via
        its own module binding, so both names must be patched together.
        """
        log_file = tmp_path / "app.log"
        log_file.write_text("hello world\n")

        with (
            patch("module.api.events.LOG_PATH", log_file),
            patch("module.api.log.LOG_PATH", log_file),
        ):
            result = await _log_payload()

        assert result == "hello world\n"
