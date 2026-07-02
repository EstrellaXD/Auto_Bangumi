"""SSE 端点：合并推送 status/downloader/log 更新，取代前端的三个轮询循环
(hooks/useAppInfo.ts:24、pages/index/downloader.vue:28、store/log.ts:25)。

单个连接按 tick 节拍分别推送三种事件，节拍与原轮询间隔保持一致，
前端订阅失败时回退到原有轮询逻辑。
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
from module.downloader import DownloadClient
from module.security.api import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])

# tick 节拍（秒）及各事件相对节拍的推送倍数，与原轮询间隔一一对应：
# status 3s、downloader 5s、log 10s。
_TICK_SECONDS = 1
_STATUS_EVERY = 3
_DOWNLOADER_EVERY = 5
_LOG_EVERY = 10


def _status_payload(ctx: AppContext) -> dict:
    """构造与 GET /program/status 相同结构的状态负载。"""
    return {
        "status": ctx.is_running,
        "version": VERSION,
        "first_run": ctx.first_run,
    }


async def _downloader_payload() -> list[dict] | None:
    """获取种子列表；下载器未配置或不可达时返回 None（跳过本次推送）。"""
    try:
        async with DownloadClient() as client:
            return await client.get_torrent_info(category="Bangumi", status_filter=None)
    except Exception:
        logger.debug("SSE: downloader status unavailable", exc_info=True)
        return None


async def _log_payload() -> str | None:
    """读取日志尾部；日志文件不存在时返回 None（跳过本次推送）。"""
    if not LOG_PATH.exists():
        return None
    data = await asyncio.to_thread(_read_log_tail)
    return data.decode("utf-8", errors="replace")


@router.get("/stream", dependencies=[Depends(get_current_user)])
async def event_stream(request: Request, ctx: AppContext = Depends(get_context)):
    """单一 SSE 连接，按各自节拍推送 status/downloader/log 事件。"""

    async def generator():
        tick = 0
        while True:
            if await request.is_disconnected():
                break

            if tick % _STATUS_EVERY == 0:
                yield {"event": "status", "data": json.dumps(_status_payload(ctx))}

            if tick % _DOWNLOADER_EVERY == 0:
                torrents = await _downloader_payload()
                if torrents is not None:
                    yield {"event": "downloader", "data": json.dumps(torrents)}

            if tick % _LOG_EVERY == 0:
                log_text = await _log_payload()
                if log_text is not None:
                    yield {"event": "log", "data": log_text}

            await asyncio.sleep(_TICK_SECONDS)
            tick += _TICK_SECONDS

    return EventSourceResponse(generator())
