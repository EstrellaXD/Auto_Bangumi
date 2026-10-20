"""Tests for the events SSE endpoint and its payload builders."""

import asyncio
import json
import os
import time
from itertools import chain, repeat
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from module.api import events, v1
from module.api.events import (
    _downloader_payload,
    _LogCursor,
    _status_payload,
    _TorrentCache,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def fresh_torrent_cache(monkeypatch):
    """种子列表缓存是模块级共享状态（含绑定事件循环的锁），每个用例换一份。"""
    monkeypatch.setattr(events, "_torrents", _TorrentCache())


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

        with patch(
            "module.downloader.download_client.DownloadClient", return_value=mock_client
        ):
            result = await _downloader_payload()

        assert result == [{**torrents[0], "downloader_id": "default"}]
        mock_client.get_torrent_info.assert_called_once_with(
            category="Bangumi", status_filter=None
        )

    async def test_downloader_payload_unavailable_returns_none(self):
        """_downloader_payload swallows client errors and returns None so the
        stream skips that tick instead of crashing the connection."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(side_effect=RuntimeError("no downloader"))
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "module.downloader.download_client.DownloadClient", return_value=mock_client
        ):
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
            patch(
                "module.downloader.download_client.DownloadClient",
                return_value=mock_client,
            ),
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
            patch(
                "module.downloader.download_client.DownloadClient",
                return_value=mock_client,
            ),
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


class TestTorrentCache:
    async def test_concurrent_streams_share_one_fetch_per_ttl(self, monkeypatch):
        """N 个连接同时取种子列表，TTL 内只查询一次下载器；过期后再查一次。"""
        fetch = AsyncMock(return_value=[{"hash": "abc"}])
        monkeypatch.setattr(events, "_downloader_payload", fetch)
        cache = _TorrentCache()

        results = await asyncio.gather(*(cache.get() for _ in range(10)))
        await cache.get()
        assert fetch.await_count == 1
        assert set(results) == {json.dumps([{"hash": "abc"}])}

        monkeypatch.setattr(events, "_DOWNLOADER_CACHE_SECONDS", 0)
        await cache.get()
        assert fetch.await_count == 2


class TestLogCursor:
    """log 帧：首帧整段尾部；之后只推新增完整行；轮转/截断后重推整段。"""

    @pytest.fixture
    def log_file(self, tmp_path):
        """_read_log_tail 通过 module.api.log 自己的 LOG_PATH 绑定读文件，两处一起替换。"""
        log_file = tmp_path / "app.log"
        with (
            patch("module.api.events.LOG_PATH", log_file),
            patch("module.api.log.LOG_PATH", log_file),
        ):
            yield log_file

    async def test_missing_file_yields_no_frame(self, log_file):
        assert await _LogCursor().frame() is None

    async def test_first_frame_is_full_tail(self, log_file):
        log_file.write_text("hello world\n")

        frame = await _LogCursor().frame()

        assert frame == {"event": "log", "data": "hello world\n"}

    @pytest.mark.parametrize(
        ("appended", "expected"),
        [
            ("second 第二行\n", "second 第二行\n"),
            # 半行留到写完整再推，偏移只前进到最后一个换行
            ("second\nthi", "second\n"),
            ("", None),
            ("thi", None),
        ],
    )
    async def test_append_yields_only_new_complete_lines(
        self, log_file, appended, expected
    ):
        log_file.write_text("hello world\n")
        cursor = _LogCursor()
        await cursor.frame()

        with log_file.open("a") as f:
            f.write(appended)
        frame = await cursor.frame()

        if expected is None:
            assert frame is None
        else:
            assert frame == {"event": "log_append", "data": expected}

    async def test_partial_line_is_sent_once_completed(self, log_file):
        log_file.write_text("hello world\n")
        cursor = _LogCursor()
        await cursor.frame()

        with log_file.open("a") as f:
            f.write("thi")
        assert await cursor.frame() is None
        with log_file.open("a") as f:
            f.write("rd\n")

        assert await cursor.frame() == {"event": "log_append", "data": "third\n"}

    async def test_cleared_log_sends_full_frame_once_it_has_content(self, log_file):
        log_file.write_text("old line\n")
        cursor = _LogCursor()
        await cursor.frame()

        log_file.write_text("")
        assert await cursor.frame() is None
        with log_file.open("a") as f:
            f.write("fresh\n")

        assert await cursor.frame() == {"event": "log", "data": "fresh\n"}

    @pytest.mark.parametrize(
        ("change", "expected"),
        [
            ("truncate", "new\n"),
            # 轮转后 log.txt 近乎为空，整段尾部会拼上 .1 备份
            ("rotate", "old line one\nold line two\nnew\n"),
            # 同 inode、同大小，但 mtime 回退（被整体替换写回）
            ("mtime_reset", "NEW line one\nNEW line two\n"),
        ],
    )
    async def test_rotation_or_truncation_yields_full_frame(
        self, log_file, change, expected
    ):
        log_file.write_text("old line one\nold line two\n")
        cursor = _LogCursor()
        await cursor.frame()

        if change == "truncate":
            log_file.write_text("new\n")
        elif change == "rotate":
            log_file.rename(log_file.with_name(f"{log_file.name}.1"))
            log_file.write_text("new\n")
        else:
            st = log_file.stat()
            log_file.write_text("NEW line one\nNEW line two\n")
            os.utime(log_file, ns=(st.st_atime_ns, st.st_mtime_ns - 10**9))

        assert await cursor.frame() == {"event": "log", "data": expected}


# ---------------------------------------------------------------------------
# notification event（通知中心未读数推送）
# ---------------------------------------------------------------------------


class TestNotificationEvent:
    """notification 帧由事件总线上的 inbox.changed 驱动（P5），线格式不变。"""

    @pytest.fixture
    def bus(self, monkeypatch):
        from module.plugin import host
        from module.plugin.bus import EventBus

        bus = EventBus()
        monkeypatch.setattr(host, "_bus", bus)
        return bus

    def _generator(self, tmp_path, *, tick=0.01, payload=None, downloader=None):
        from module.api.events import _event_generator

        request = AsyncMock()
        request.is_disconnected = AsyncMock(return_value=False)
        ctx = MagicMock()
        ctx.is_running = True
        ctx.first_run = False
        notification = payload or AsyncMock(
            return_value={"unread_count": 2, "latest_id": 9}
        )
        patches = (
            patch(
                "module.api.events._downloader_payload",
                new=downloader or AsyncMock(return_value=None),
            ),
            patch("module.api.events.LOG_PATH", tmp_path / "missing.log"),
            patch("module.api.events._notification_payload", new=notification),
            patch("module.api.events._TICK_SECONDS", tick),
        )
        return _event_generator(request, ctx), patches

    async def _collect(self, gen, n):
        events = []
        for _ in range(n):
            events.append(await asyncio.wait_for(gen.__anext__(), timeout=1.0))
        return events

    async def test_first_tick_emits_notification_frame(self, tmp_path, bus):
        from module.notification.inbox import inbox_revision

        gen, patches = self._generator(tmp_path)
        with patches[0], patches[1], patches[2], patches[3]:
            try:
                events = await self._collect(gen, 3)
            finally:
                await gen.aclose()

        assert [e["event"] for e in events] == ["status", "downloader", "notification"]
        # 线格式与 3.x 一致：unread_count / latest_id / revision 三个字段
        data = json.loads(events[2]["data"])
        assert data == {"unread_count": 2, "latest_id": 9, "revision": inbox_revision()}

    async def test_no_frame_without_inbox_change(self, tmp_path, bus):
        gen, patches = self._generator(tmp_path)
        with patches[0], patches[1], patches[2], patches[3]:
            try:
                await self._collect(gen, 3)  # 第一个 tick
                # tick3 status、tick6 status（tick5 的 downloader 负载未变，不推）
                # —— 中间不应再有 notification
                more = await self._collect(gen, 2)
            finally:
                await gen.aclose()

        assert [e["event"] for e in more] == ["status", "status"]

    @pytest.mark.parametrize(
        ("second", "expected"),
        [
            (
                [{"hash": "a"}],
                ["status", "downloader", "notification", "status", "status"],
            ),
            (
                [{"hash": "b"}],
                ["status", "downloader", "notification", "status", "downloader"],
            ),
        ],
    )
    async def test_downloader_frame_only_when_payload_changes(
        self, tmp_path, bus, monkeypatch, second, expected
    ):
        fetch = AsyncMock(side_effect=chain([[{"hash": "a"}]], repeat(second)))
        monkeypatch.setattr(events, "_DOWNLOADER_CACHE_SECONDS", 0)
        gen, patches = self._generator(tmp_path, downloader=fetch)
        with patches[0], patches[1], patches[2], patches[3]:
            try:
                got = await self._collect(gen, 5)  # tick0 … tick5
            finally:
                await gen.aclose()

        assert [e["event"] for e in got] == expected
        assert fetch.await_count == 2

    async def test_inbox_change_pushes_frame_immediately(self, tmp_path, bus):
        from module.notification.inbox import bump_inbox_revision, inbox_revision

        # tick 设为 30s：若不是事件推送，1s 内不可能收到下一帧
        gen, patches = self._generator(tmp_path, tick=30)
        with patches[0], patches[1], patches[2], patches[3]:
            try:
                await self._collect(gen, 3)  # 第一个 tick
                bump_inbox_revision()
                [frame] = await self._collect(gen, 1)
            finally:
                await gen.aclose()

        assert frame["event"] == "notification"
        assert json.loads(frame["data"])["revision"] == inbox_revision()

    async def test_bus_event_is_forwarded_as_bus_frame(self, tmp_path, bus):
        from dataclasses import dataclass
        from typing import ClassVar

        from ab_sdk import Event

        @dataclass(frozen=True, slots=True)
        class Picked(Event):
            kind: ClassVar[str] = "demo.picked"
            torrent_id: int

        gen, patches = self._generator(tmp_path, tick=30)
        with patches[0], patches[1], patches[2], patches[3]:
            try:
                await self._collect(gen, 3)  # 第一个 tick
                bus.publish(Picked(torrent_id=7))
                [frame] = await self._collect(gen, 1)
            finally:
                await gen.aclose()

        assert frame["event"] == "bus"
        assert json.loads(frame["data"]) == {
            "kind": "demo.picked",
            "payload": {"torrent_id": 7},
        }

    async def test_unsubscribes_when_stream_closes(self, tmp_path, bus):
        gen, patches = self._generator(tmp_path)
        with patches[0], patches[1], patches[2], patches[3]:
            await self._collect(gen, 3)
            assert len(bus._subscribers) == 1
            await gen.aclose()
        assert bus._subscribers == []

    async def test_failed_query_is_retried_next_tick(self, tmp_path, bus):
        payload = AsyncMock(
            side_effect=[RuntimeError("db busy"), {"unread_count": 1, "latest_id": 3}]
        )
        gen, patches = self._generator(tmp_path, payload=payload)
        with patches[0], patches[1], patches[2], patches[3]:
            try:
                events = await self._collect(gen, 3)
            finally:
                await gen.aclose()

        # tick0：status + downloader（notification 查库失败）；tick1 重试成功
        assert [e["event"] for e in events] == ["status", "downloader", "notification"]
        assert json.loads(events[2]["data"])["latest_id"] == 3
        assert payload.await_count == 2

    async def test_without_bus_only_initial_frame(self, tmp_path, monkeypatch):
        from module.plugin import host

        monkeypatch.setattr(host, "_bus", None)
        gen, patches = self._generator(tmp_path)
        with patches[0], patches[1], patches[2], patches[3]:
            try:
                events = await self._collect(gen, 5)
            finally:
                await gen.aclose()

        assert [e["event"] for e in events].count("notification") == 1
