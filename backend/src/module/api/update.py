"""在线自动更新 API：检查 / 应用 / 回滚。

三个端点均由 ``get_current_user`` 鉴权保护。``apply`` / ``rollback`` 成功后会
安排一次延迟进程退出——退出前写入 ``config/updates/.restart``，entrypoint
内部循环会重跑覆盖层逻辑并再次启动应用。

进程退出被抽成可打桩的 ``schedule_restart``，测试据此断言“已安排重启”而不会真的
退出进程。
"""

import asyncio
import logging
import os
import signal
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from module.conf import settings
from module.security.api import get_current_user
from module.update import updater

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/update", tags=["update"])

# 退出前的延迟：先让 HTTP 响应与最后一帧 SSE 进度刷出，再退出进程。
_RESTART_DELAY_SECONDS = 1.5
RESTART_SENTINEL = Path("config") / "updates" / ".restart"
_RESTART_TASKS: set[asyncio.Task] = set()


def _request_restart() -> None:
    """请求 entrypoint 内部循环重启进程并重跑覆盖层。"""
    logger.info("restarting process to apply update")
    RESTART_SENTINEL.parent.mkdir(parents=True, exist_ok=True)
    RESTART_SENTINEL.touch()
    os.kill(os.getpid(), signal.SIGINT)


async def _delayed_restart() -> None:
    await asyncio.sleep(_RESTART_DELAY_SECONDS)
    _request_restart()


def schedule_restart() -> None:
    """安排一次延迟重启（抽成独立函数以便测试打桩，避免真的退出进程）。"""
    task = asyncio.create_task(_delayed_restart())
    _RESTART_TASKS.add(task)
    task.add_done_callback(_RESTART_TASKS.discard)


@router.get("/check", dependencies=[Depends(get_current_user)])
async def check_update(channel: str | None = None, force: bool = False):
    """查询 GitHub Release，返回最新版本、更新提示与本地覆盖层状态。

    ``force=True``（用户点“检查更新”）绕过 15 分钟结果缓存重新拉取；
    进入设置页时的自动检查用 ``force=False`` 走缓存，避免频繁打 GitHub API。
    """
    ch = channel or settings.update.channel
    result = await updater.check_update(ch, force=force)
    return result.model_dump()


@router.post("/apply", dependencies=[Depends(get_current_user)])
async def apply_update(channel: str | None = None):
    """下载并落地最新更新；成功后安排进程重启以生效。"""
    ch = channel or settings.update.channel
    result = await updater.apply_update(ch)
    if result.success and result.restart_required:
        schedule_restart()
    return JSONResponse(
        status_code=200 if result.success else 400,
        content=result.model_dump(),
    )


@router.post("/rollback", dependencies=[Depends(get_current_user)])
async def rollback_update():
    """回滚到上一个覆盖层版本（无备份则回退到镜像版本）；成功后安排重启。"""
    result = await updater.rollback()
    if result.success and result.restart_required:
        schedule_restart()
    return JSONResponse(
        status_code=200 if result.success else 400,
        content=result.model_dump(),
    )
