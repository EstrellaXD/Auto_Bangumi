import logging
import os
import signal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from module.core import Program
from module.models import APIResponse
from module.conf import VERSION
from module.security.api import get_current_user, UNAUTHORIZED

logger = logging.getLogger(__name__)
program = Program()
router = APIRouter(tags=["program"])


@router.on_event("startup")
async def startup():
    program.startup()


@router.on_event("shutdown")
async def shutdown():
    program.stop()


@router.get("/restart", response_model=APIResponse)
async def restart(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    try:
        program.restart()
        return JSONResponse(
            status_code=200,
            content={"msg_en": "Restart program successfully.", "msg_zh": "重启程序成功。"},
        )
    except Exception as e:
        logger.debug(e)
        logger.warning("Failed to restart program")
        raise HTTPException(
            status_code=500,
            detail={
                "msg_en": "Failed to restart program.",
                "msg_zh": "重启程序失败。",
           }
        )


@router.get("/start", response_model=APIResponse)
async def start(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    try:
        return program.start()
    except Exception as e:
        logger.debug(e)
        logger.warning("Failed to start program")
        raise HTTPException(
            status_code=500,
            detail={
                "msg_en": "Failed to start program.",
                "msg_zh": "启动程序失败。",
            }
        )


@router.get("/stop")
async def stop(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    return program.stop()


@router.get("/status")
async def program_status(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    if not program.is_running:
        return {
            "status": False,
            "version": VERSION,
        }
    else:
        return {
            "status": True,
            "version": VERSION,
        }


@router.get("/shutdown")
async def shutdown_program(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    program.stop()
    logger.info("Shutting down program...")
    os.kill(os.getpid(), signal.SIGINT)
    return JSONResponse(
        status_code=200,
        content={"msg_en": "Shutdown program successfully.", "msg_zh": "关闭程序成功。"},
    )


# Check status
@router.get("/check/downloader", tags=["check"], response_model=bool)
async def check_downloader_status(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    return program.check_downloader()
