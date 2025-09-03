import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from module.conf import VERSION
from module.core import Program
from module.models import APIResponse
from module.models.response import ResponseModel
from module.security.api import get_current_user
from module.update import ReleaseChecker

from .response import u_response

logger = logging.getLogger(__name__)
program = Program()
router = APIRouter(tags=["program"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动事件
    # 首先检查数据库版本并升级
    logger.info("检查数据库版本兼容性...")

    await program.startup()
    yield
    # 关闭事件
    await program.stop()


@router.get("/restart", response_model=APIResponse, dependencies=[Depends(get_current_user)])
async def restart():
    try:
        await program.restart()
        return u_response(
            ResponseModel(
                status=True,
                status_code=200,
                msg_en="Program restarted.",
                msg_zh="程序重启成功。",
            )
        )
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


@router.get("/start", response_model=APIResponse, dependencies=[Depends(get_current_user)])
async def start():
    try:
        await program.start()
        return u_response(
            ResponseModel(
                status=True,
                status_code=200,
                msg_en="Program started.",
                msg_zh="程序启动成功。",
            )
        )
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


@router.get("/stop", response_model=APIResponse, dependencies=[Depends(get_current_user)])
async def stop():
    await program.stop()
    return u_response(
        ResponseModel(
            status=True,
            status_code=200,
            msg_en="Program stopped.",
            msg_zh="程序停止成功。",
        )
    )


@router.get("/status", response_model=dict, dependencies=[Depends(get_current_user)])
async def program_status():
    if not program.program_status.is_running:
        return {
            "status": False,
            "version": VERSION,
            "first_run": program.program_status.first_run,
        }
    else:
        return {
            "status": True,
            "version": VERSION,
            "first_run": program.program_status.first_run,
        }


@router.get("/shutdown", response_model=APIResponse, dependencies=[Depends(get_current_user)])
async def shutdown_program():
    await program.stop()
    logger.info("Shutting down program...")
    # os.kill(os.getpid(), signal.SIGINT)
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
async def check_downloader_status():
    return program.program_status.check_downloader()


# Check for updates
@router.get(
    "/check/update",
    tags=["update"],
    response_model=dict,
    dependencies=[Depends(get_current_user)],
)
async def check_for_update(include_prerelease: bool = False):
    """检查是否有可用的版本更新

    Args:
        include_prerelease: 是否包含预发布版本

    Returns:
        dict: 包含版本检查结果的字典
    """
    try:
        checker = ReleaseChecker("shinonomeow", "Auto_Bangumi")
        result = await checker.check_for_update(include_prerelease=True)
        return result
    except Exception as e:
        logger.error(f"Failed to check for updates: {e}")
        raise HTTPException(
            status_code=500,
            detail={"msg_en": "Failed to check for updates.", "msg_zh": "检查更新失败。", "error": str(e)},
        )


@router.post("/program/update", response_model=APIResponse, dependencies=[Depends(get_current_user)])
async def update_program(download_url: str):
    """Docker 环境更新接口

    Args:
        download_url: 更新包下载 URL（必须是 GitHub releases）

    Returns:
        APIResponse: 更新结果
    """
    try:
        # 检测是否在 Docker 环境
        from module.utils.environment import is_docker_environment

        if not is_docker_environment():
            return u_response(
                ResponseModel(
                    status=False,
                    status_code=400,
                    msg_en="Update only supported in Docker environment.",
                    msg_zh="更新功能仅支持 Docker 环境。",
                )
            )

        # 导入更新器
        from module.update import docker_updater

        # 创建异步任务执行更新
        async def perform_update():
            try:
                # 等待一小段时间让 API 响应返回
                await asyncio.sleep(1)

                logger.info(f"[Program] Starting update preparation from URL: {download_url}")

                # 停止应用核心
                await program.stop()

                # 准备更新：下载、解压、创建标志文件
                await docker_updater.prepare_update(download_url)

                # 触发优雅重启，shell脚本会检测更新标志并执行替换
                docker_updater.trigger_graceful_restart()

            except Exception as e:
                logger.error(f"[Program] Update preparation failed: {e}")
                # 尝试重启应用核心
                try:
                    await program.start()
                except Exception as restart_error:
                    logger.error(f"[Program] Failed to restart after update failure: {restart_error}")

        # 启动异步更新任务
        asyncio.create_task(perform_update())

        # 立即返回响应
        return u_response(
            ResponseModel(
                status=True,
                status_code=200,
                msg_en="Update started successfully. Container will restart shortly.",
                msg_zh="更新已开始。容器将很快重启。",
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Program] Update initiation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"msg_en": "Failed to start update process.", "msg_zh": "启动更新进程失败。", "error": str(e)},
        )


# Update status check
@router.get("/update/status", response_model=dict, dependencies=[Depends(get_current_user)])
async def get_update_status():
    """获取更新状态

    Returns:
        dict: 更新状态信息
    """
    import os

    from module.utils.environment import get_environment_info, is_docker_environment

    # 检查是否有更新锁文件
    update_lock_exists = os.path.exists("/tmp/auto_bangumi_update.lock")

    return {
        "update_in_progress": update_lock_exists,
        "environment": get_environment_info(),
        "update_supported": is_docker_environment(),
    }
