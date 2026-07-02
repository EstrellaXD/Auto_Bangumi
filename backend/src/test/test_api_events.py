"""Tests for the events SSE endpoint and its payload builders."""

import asyncio
import json
import time
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


def _make_hung_client(cancelled: asyncio.Event) -> AsyncMock:
    """Build a DownloadClient mock whose torrent fetch hangs until cancelled,
    setting `cancelled` when the hung task is actually torn down."""

    async def hung_fetch(*args, **kwargs):
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            cancelled.set()
            raise
        return []

    mock_client = AsyncMock()
    mock_client.get_torrent_info = hung_fetch
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


class TestDownloaderPayloadTimeout:
    async def test_downloader_payload_hung_fetch_returns_none_and_cancels_task(self):
        """A downloader fetch exceeding the timeout returns None promptly and
        the hung task is cancelled rather than leaked."""
        cancelled = asyncio.Event()
        mock_client = _make_hung_client(cancelled)

        with (
            patch("module.api.events.DownloadClient", return_value=mock_client),
            patch("module.api.events._DOWNLOADER_TIMEOUT_SECONDS", 0.05),
        ):
            start = time.monotonic()
            result = await _downloader_payload()
            elapsed = time.monotonic() - start

        assert result is None
        assert elapsed < 1.0
        assert cancelled.is_set()


class TestEventGeneratorNonBlocking:
    async def test_event_generator_hung_downloader_emits_status_and_null_downloader(
        self, tmp_path
    ):
        """With an unreachable downloader, the stream still yields the status
        event promptly and emits an explicit null downloader payload instead
        of stalling the whole connection."""
        from module.api.events import _event_generator

        request = AsyncMock()
        request.is_disconnected = AsyncMock(return_value=False)
        ctx = MagicMock()
        ctx.is_running = True
        ctx.first_run = False

        cancelled = asyncio.Event()
        mock_client = _make_hung_client(cancelled)

        with (
            patch("module.api.events.DownloadClient", return_value=mock_client),
            patch("module.api.events._DOWNLOADER_TIMEOUT_SECONDS", 0.05),
            patch("module.api.events.LOG_PATH", tmp_path / "missing.log"),
        ):
            gen = _event_generator(request, ctx)
            try:
                # 第一个 tick 内 status 与 downloader 事件都应在超时上限内到达
                status_event = await asyncio.wait_for(gen.__anext__(), timeout=1.0)
                downloader_event = await asyncio.wait_for(gen.__anext__(), timeout=1.0)
            finally:
                await gen.aclose()

        assert status_event["event"] == "status"
        assert json.loads(status_event["data"])["status"] is True
        assert downloader_event["event"] == "downloader"
        assert json.loads(downloader_event["data"]) is None


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
