"""SSE 端点：合并推送 status/downloader/log 更新，取代前端的三个轮询循环
(hooks/useAppInfo.ts:24、pages/index/downloader.vue:28、store/log.ts:25)。

单个连接按 tick 节拍分别推送 status/downloader/log/update，节拍与原轮询间隔
保持一致，前端订阅失败时回退到原有轮询逻辑。这几类是「状态快照」而非事件，
仍按节拍采样。

notification（通知中心未读数）由事件驱动：每个连接在插件事件总线上订阅
``inbox.changed``（通知中心写入/已读/删除时发布），收到后立即查库推送，
不再按节拍比较修订号。连接建立时推送一帧作为初始状态。
"""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from module.api.deps import get_context
from module.api.log import _read_log_tail
from module.conf import LOG_PATH, VERSION
from module.core import AppContext
from module.database import Database
from module.downloader import DownloadClient
from module.notification.inbox import InboxChanged, inbox_revision
from module.plugin.host import get_bus
from module.security.api import get_current_user
from module.update.updater import get_update_progress

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])

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


def _status_payload(ctx: AppContext) -> dict:
    """构造与 GET /program/status 相同结构的状态负载。"""
    return {
        "status": ctx.is_running,
        "version": VERSION,
        "first_run": ctx.first_run,
    }


async def _fetch_torrents() -> list[dict]:
    async with DownloadClient() as client:
        return await client.get_torrent_info(category="Bangumi", status_filter=None)


async def _downloader_payload() -> list[dict] | None:
    """获取种子列表；下载器未配置、不可达或超时时返回 None。

    asyncio.wait_for 超时会取消内部任务并等待其退出，慢查询不会泄漏；
    None 会以 null 推送给前端，作为显式的"下载器不可用"信号。
    """
    try:
        return await asyncio.wait_for(_fetch_torrents(), _DOWNLOADER_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        logger.debug("SSE: downloader status fetch timed out")
        return None
    except Exception:
        logger.debug("SSE: downloader status unavailable", exc_info=True)
        return None


async def _notification_payload() -> dict:
    """通知中心未读数 + 最新消息 id（前端据 latest_id 区分新消息与已读操作）。"""
    async with Database() as db:
        return {
            "unread_count": await db.inbox.unread_count(),
            "latest_id": await db.inbox.latest_id(),
        }


async def _log_payload() -> str | None:
    """读取日志尾部；日志文件不存在时返回 None（跳过本次推送）。"""
    if not LOG_PATH.exists():
        return None
    data = await asyncio.to_thread(_read_log_tail)
    return data.decode("utf-8", errors="replace")


class _InboxWatch:
    """一个 SSE 连接对通知中心变化的订阅。

    总线回调只置位 ``wake``；``pending`` 表示还欠前端一帧（初始帧、或上次查库
    失败需要重试）。帧的 ``revision`` 取推送时的修订号，与旧版轮询一致。
    """

    def __init__(self) -> None:
        self.wake = asyncio.Event()
        self.pending = True
        bus = get_bus()
        self._unsubscribe = (
            bus.subscribe(InboxChanged.kind, self._on_change)
            if bus is not None
            else None
        )

    def _on_change(self, _event) -> None:
        self.wake.set()

    def close(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    async def frame(self) -> dict | None:
        """有待推送的变化时查库并返回 SSE 帧；没有或查库失败时返回 None。"""
        if self.wake.is_set():
            self.wake.clear()
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
        """等到 ``deadline``（事件循环时间）或通知中心有变化；有变化返回 True。"""
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            return False
        try:
            await asyncio.wait_for(self.wake.wait(), remaining)
        except TimeoutError:
            return False
        return True


async def _event_generator(request: Request, ctx: AppContext):
    """按各自节拍推送 status/downloader/log 事件、按需推送 notification 的核心循环。"""
    loop = asyncio.get_running_loop()
    inbox = _InboxWatch()
    tick = 0
    last_update: str | None = None
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
                torrents = await _downloader_payload()
                yield {"event": "downloader", "data": json.dumps(torrents)}

            if tick % _LOG_EVERY == 0:
                log_text = await _log_payload()
                if log_text is not None:
                    yield {"event": "log", "data": log_text}

            # 通知中心：连接建立时的初始帧，以及此前查库失败后的重试
            frame = await inbox.frame()
            if frame is not None:
                yield frame

            # 等待下一个 tick；其间 inbox.changed 到达时立即推送
            deadline = loop.time() + _TICK_SECONDS
            while await inbox.wait(deadline):
                frame = await inbox.frame()
                if frame is not None:
                    yield frame
            tick += 1
    finally:
        inbox.close()


@router.get("/stream", dependencies=[Depends(get_current_user)])
async def event_stream(request: Request, ctx: AppContext = Depends(get_context)):
    """单一 SSE 连接，按各自节拍推送 status/downloader/log 事件，
    通知中心有变化时推送 notification 事件。"""
    return EventSourceResponse(_event_generator(request, ctx))
