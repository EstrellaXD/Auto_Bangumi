import logging
import os
import signal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from module.conf import VERSION
from module.core import AppContext
from module.models import APIResponse
from module.security.api import get_current_user

from .deps import get_context
from .response import u_response

logger = logging.getLogger(__name__)
router = APIRouter(tags=["program"])


# Note: Lifespan events (startup/shutdown) are handled in main.py via the
# lifespan context manager; the AppContext is injected here per-request.


@router.post(
    "/restart", response_model=APIResponse, dependencies=[Depends(get_current_user)]
)
async def restart(ctx: AppContext = Depends(get_context)):
    try:
        resp = await ctx.restart()
        return u_response(resp)
    except Exception as e:
        logger.debug(e)
        logger.warning("Failed to restart program")
        raise HTTPException(
            status_code=500,
            detail={
                "msg_en": "Failed to restart program.",
                "msg_zh": "重启程序失败。",
            },
        )


@router.post(
    "/start", response_model=APIResponse, dependencies=[Depends(get_current_user)]
)
async def start(ctx: AppContext = Depends(get_context)):
    try:
        resp = await ctx.start_tasks()
        return u_response(resp)
    except Exception as e:
        logger.debug(e)
        logger.warning("Failed to start program")
        raise HTTPException(
            status_code=500,
            detail={
                "msg_en": "Failed to start program.",
                "msg_zh": "启动程序失败。",
            },
        )


@router.post(
    "/stop", response_model=APIResponse, dependencies=[Depends(get_current_user)]
)
async def stop(ctx: AppContext = Depends(get_context)):
    resp = await ctx.stop()
    return u_response(resp)


@router.get("/status", response_model=dict, dependencies=[Depends(get_current_user)])
async def program_status(ctx: AppContext = Depends(get_context)):
    if not ctx.is_running:
        return {
            "status": False,
            "version": VERSION,
            "first_run": ctx.first_run,
        }
    else:
        return {
            "status": True,
            "version": VERSION,
            "first_run": ctx.first_run,
        }


@router.post(
    "/shutdown", response_model=APIResponse, dependencies=[Depends(get_current_user)]
)
async def shutdown_program(ctx: AppContext = Depends(get_context)):
    await ctx.stop()
    logger.info("Shutting down program...")
    os.kill(os.getpid(), signal.SIGINT)
    return JSONResponse(
        status_code=200,
        content={
            "msg_en": "Shutdown program successfully.",
            "msg_zh": "关闭程序成功。",
        },
    )


# Check status
@router.get(
    "/check/downloader",
    tags=["check"],
    response_model=bool,
    dependencies=[Depends(get_current_user)],
)
async def check_downloader_status(ctx: AppContext = Depends(get_context)):
    return await ctx.check_downloader()


# 3.2 兼容：这些控制端点在 3.2 及更早版本是 GET，外部自动化（cron/Home
# Assistant 等）沿用旧方法，升级后不得 405 静默失效。GET 别名标记为
# deprecated，计划下个大版本移除。
for _path, _endpoint in (
    ("/restart", restart),
    ("/start", start),
    ("/stop", stop),
    ("/shutdown", shutdown_program),
):
    router.add_api_route(
        _path,
        _endpoint,
        methods=["GET"],
        response_model=APIResponse,
        dependencies=[Depends(get_current_user)],
        deprecated=True,
    )
