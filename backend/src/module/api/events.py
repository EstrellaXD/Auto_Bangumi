"""SSE 端点：合并推送 status/downloader/log 更新，取代前端的三个轮询循环
(hooks/useAppInfo.ts:24、pages/index/downloader.vue:28、store/log.ts:25)。

单个连接按 tick 节拍分别推送 status/downloader/log/update，节拍与原轮询间隔
保持一致，前端订阅失败时回退到原有轮询逻辑。这几类是「状态快照」而非事件，
仍按节拍采样，但只推变化：

- downloader：所有连接共用一份 5s 缓存查询下载器；连接建立时推一帧，之后
  仅在负载与本连接上次推送的不同时才推。
- log：连接建立时、以及日志被轮转/截断后推整段尾部（``log``，日志为空时推
  ``log_clear``）；其余只推上次之后新增的完整行（``log_append``，总以换行
  结尾），没有新增不推。

notification（通知中心未读数）由事件驱动：每个连接在插件事件总线上订阅
``inbox.changed``（通知中心写入/已读/删除时发布），收到后立即查库推送，
不再按节拍比较修订号。连接建立时推送一帧作为初始状态。

总线上的其它事件（宿主与插件发布的）以 ``bus`` 帧转发，供前端插件组件的
``host.events.on(kind, ...)`` 订阅；帧为 ``{"kind": ..., "payload": {...}}``。
"""

import asyncio
import dataclasses
import json
import logging
import os
import time
from collections import deque
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent

from ab_sdk import Event
from module.api import log as log_api
from module.api.deps import get_context
from module.api.log import _read_log_tail
from module.conf import LOG_PATH, VERSION
from module.core import AppContext
from module.database import Database
from module.downloader import list_torrents
from module.notification.inbox import InboxChanged, inbox_revision
from module.plugin.bus import ALL_EVENTS
from module.plugin.host import get_bus
from module.security.api import get_current_user
from module.update.updater import get_update_progress

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/events", tags=["events"], dependencies=[Depends(get_current_user)]
)


# tick 节拍（秒）及各事件相对节拍的推送倍数，与原轮询间隔一一对应：
# status 3s、downloader 5s、log 10s。
_TICK_SECONDS = 1
_STATUS_EVERY = 3
_DOWNLOADER_EVERY = 5
_LOG_EVERY = 10

# 下载器查询的超时上限（秒）。下载器不可达时 qB/aria2 的认证重试可能阻塞
# 20-30s，而 SSE 是单连接串行推送——不设上限会把 status/log 事件一起卡住。
# 取值需明显小于 downloader 的 5s 推送间隔。
_DOWNLOADER_TIMEOUT_SECONDS = 3.0

# 下载器种子列表的共享缓存有效期（秒）：所有 SSE 连接合计每 5s 最多查询一次
_DOWNLOADER_CACHE_SECONDS = 5.0

# 单个连接最多积压的待转发总线事件数
_FORWARD_BACKLOG = 200


def _status_payload(ctx: AppContext) -> dict:
    """构造与 GET /program/status 相同结构的状态负载。"""
    return {
        "status": ctx.is_running,
        "version": VERSION,
        "first_run": ctx.first_run,
    }


async def _downloader_payload() -> list[dict] | None:
    """获取所有下载器实例的种子列表；全部实例不可达或超时时返回 None。

    超时按实例计算，一个实例不可用不影响其它实例的种子；asyncio.wait_for
    超时会取消内部任务并等待其退出，慢查询不会泄漏。None 会以 null 推送给
    前端，作为显式的"下载器不可用"信号。
    """
    return await list_torrents(timeout=_DOWNLOADER_TIMEOUT_SECONDS)


async def _notification_payload() -> dict:
    """通知中心未读数 + 最新消息 id（前端据 latest_id 区分新消息与已读操作）。"""
    async with Database() as db:
        return {
            "unread_count": await db.inbox.unread_count(),
            "latest_id": await db.inbox.latest_id(),
        }


class _TorrentCache:
    """所有 SSE 连接共用的种子列表缓存（已编码为 JSON）。

    锁保证并发连接同一时刻只查一次下载器；时间戳记在查询开始时，
    连接按约 5s 的节拍来取时不会拿到隔一轮的旧数据。
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._fetched_at = -_DOWNLOADER_CACHE_SECONDS
        self._data: str | None = None

    async def get(self) -> str:
        async with self._lock:
            now = time.monotonic()
            if (
                self._data is None
                or now - self._fetched_at >= _DOWNLOADER_CACHE_SECONDS
            ):
                # 查询被取消（持锁的连接断开）时不更新时间戳，下一个连接重新查询
                self._data = json.dumps(await _downloader_payload())
                self._fetched_at = now
            return self._data


_torrents = _TorrentCache()


class _LogCursor:
    """一个 SSE 连接的日志读取位置。

    首帧及日志被轮转（inode 变化）、截断（大小小于已读偏移）、mtime 回退或
    经 /log/clear 清空（清空计数变化）时推整段尾部 ``log``（为空时推
    ``log_clear``）；否则只推偏移
    之后新增的完整行 ``log_append``。增量截到最后一个换行：不切断多字节
    字符，且每帧都是完整行，前端可直接追加。
    """

    def __init__(self) -> None:
        self._ino: int | None = None
        self._mtime_ns = 0
        self._offset = 0
        self._generation = -1

    def _read(self) -> dict | None:
        try:
            st = os.stat(LOG_PATH)
            generation = log_api._clear_generation
            if (
                generation == self._generation
                and st.st_ino == self._ino
                and st.st_size >= self._offset
                and st.st_mtime_ns >= self._mtime_ns
            ):
                self._mtime_ns = st.st_mtime_ns
                if st.st_size == self._offset:
                    return None
                with open(LOG_PATH, "rb") as f:
                    f.seek(self._offset)
                    data = f.read(st.st_size - self._offset)
                data = data[: data.rfind(b"\n") + 1]
                if not data:
                    return None
                self._offset += len(data)
                event = "log_append"
            else:
                data, offset = _read_log_tail()
                self._ino, self._mtime_ns, self._offset, self._generation = (
                    st.st_ino,
                    st.st_mtime_ns,
                    offset,
                    generation,
                )
                event = "log"
                if not data:
                    # EventSource 不派发 data 为空的事件：空日志改推 log_clear，
                    # 别的标签页清空后、或清空后重连时前端才不会残留旧日志
                    event, data = "log_clear", b"1"
        except FileNotFoundError:
            # 尚未创建，或正处于轮转改名的间隙：本轮跳过
            return None
        return {"event": event, "data": data.decode("utf-8", errors="replace")}

    async def frame(self) -> dict | None:
        return await asyncio.to_thread(self._read)


class _InboxWatch:
    """一个 SSE 连接对事件总线的订阅：通知中心变化与待转发的其它事件。

    总线回调只置位 ``wake``；``pending`` 表示还欠前端一帧（初始帧、或上次查库
    失败需要重试）。帧的 ``revision`` 取推送时的修订号，与旧版轮询一致。
    """

    def __init__(self) -> None:
        self.wake = asyncio.Event()
        self.pending = True
        self._inbox_changed = False
        # 前端来不及消费时丢最旧的，不让一个慢连接无限堆积
        self._forward: deque[dict] = deque(maxlen=_FORWARD_BACKLOG)
        bus = get_bus()
        self._unsubscribe = (
            bus.subscribe(ALL_EVENTS, self._on_event) if bus is not None else None
        )

    def _on_event(self, event: Event) -> None:
        if event.kind == InboxChanged.kind:
            self._inbox_changed = True
        else:
            payload = (
                dataclasses.asdict(event) if dataclasses.is_dataclass(event) else {}
            )
            self._forward.append(
                {
                    "event": "bus",
                    "data": json.dumps(
                        {"kind": event.kind, "payload": payload}, default=str
                    ),
                }
            )
        self.wake.set()

    def close(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    def forwarded(self) -> list[dict]:
        """取走待转发的总线事件帧。"""
        frames = list(self._forward)
        self._forward.clear()
        return frames

    async def frame(self) -> dict | None:
        """有待推送的变化时查库并返回 SSE 帧；没有或查库失败时返回 None。"""
        if self._inbox_changed:
            self._inbox_changed = False
            self.pending = True
        if not self.pending:
            return None
        rev = inbox_revision()
        try:
            payload = await _notification_payload()
        except Exception:
            logger.debug("SSE: notification payload unavailable", exc_info=True)
            return None
        self.pending = False
        payload["revision"] = rev
        return {"event": "notification", "data": json.dumps(payload)}

    async def wait(self, deadline: float) -> bool:
        """等到 ``deadline``（事件循环时间）或总线有事件；有事件返回 True。"""
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            return False
        try:
            await asyncio.wait_for(self.wake.wait(), remaining)
        except TimeoutError:
            return False
        self.wake.clear()
        return True


async def _event_generator(request: Request, ctx: AppContext):
    """按各自节拍推送 status/downloader/log 事件、按需推送 notification 的核心循环。"""
    loop = asyncio.get_running_loop()
    inbox = _InboxWatch()
    log = _LogCursor()
    tick = 0
    last_update: str | None = None
    last_downloader: str | None = None
    try:
        while True:
            if await request.is_disconnected():
                break

            # 更新进度：仅在有进行中的更新（phase != idle）且负载变化时推送，
            # 避免重复帧刷屏；每 tick 检查一次以保证下载进度足够实时。
            progress = get_update_progress()
            if progress.get("phase") != "idle":
                payload = json.dumps(progress)
                if payload != last_update:
                    last_update = payload
                    yield {"event": "update", "data": payload}

            if tick % _STATUS_EVERY == 0:
                yield {"event": "status", "data": json.dumps(_status_payload(ctx))}

            if tick % _DOWNLOADER_EVERY == 0:
                # 不可用时推送 null 而非跳过，前端据此感知下载器降级状态
                # （store/downloader.ts 对 null 保留旧数据，不会崩溃）。
                torrents = await _torrents.get()
                if torrents != last_downloader:
                    last_downloader = torrents
                    yield {"event": "downloader", "data": torrents}

            if tick % _LOG_EVERY == 0:
                log_frame = await log.frame()
                if log_frame is not None:
                    yield log_frame

            # 通知中心：连接建立时的初始帧，以及此前查库失败后的重试
            frame = await inbox.frame()
            if frame is not None:
                yield frame
            for frame in inbox.forwarded():
                yield frame

            # 等待下一个 tick；其间总线事件到达时立即推送
            deadline = loop.time() + _TICK_SECONDS
            while await inbox.wait(deadline):
                frame = await inbox.frame()
                if frame is not None:
                    yield frame
                for frame in inbox.forwarded():
                    yield frame
            tick += 1
    finally:
        inbox.close()


@router.get("/stream", response_class=EventSourceResponse)
async def event_stream(
    request: Request, ctx: AppContext = Depends(get_context)
) -> AsyncIterator[ServerSentEvent]:
    """单一 SSE 连接，按各自节拍推送 status/downloader/log 事件，
    通知中心有变化时推送 notification 事件。"""
    # 帧数据已是编码好的字符串（log 为原始文本），用 raw_data 避免再做一次 JSON 编码
    async for frame in _event_generator(request, ctx):
        yield ServerSentEvent(event=frame["event"], raw_data=frame["data"])
