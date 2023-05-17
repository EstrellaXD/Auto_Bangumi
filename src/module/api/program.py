import os
import signal
import logging
import asyncio

from fastapi.exceptions import HTTPException

from .download import router

from module.core import Program, check_status, check_rss, check_downloader

logger = logging.getLogger(__name__)
program = Program()


@router.on_event("startup")
async def on_startup():
    asyncio.create_task(program.startup())


@router.on_event("shutdown")
def shutdown():
    program.stop()
    logger.info("Stopping program...")


@router.get("/api/v1/restart", tags=["program"])
async def restart():
    try:
        program.restart()
        return {"status": "ok"}
    except Exception as e:
        logger.debug(e)
        logger.warning("Failed to restart program")
        raise HTTPException(status_code=500, detail="Failed to restart program")


@router.get("/api/v1/start", tags=["program"])
async def start():
    try:
        program.start()
        return {"status": "ok"}
    except Exception as e:
        logger.debug(e)
        logger.warning("Failed to start program")
        raise HTTPException(status_code=500, detail="Failed to start program")


@router.get("/api/v1/stop", tags=["program"])
async def stop():
    program.stop()
    return {"status": "ok"}


@router.get("/api/v1/status", tags=["program"])
async def status():
    if not program.is_running:
        return {"status": "stop"}
    else:
        return {"status": "running"}


@router.get("/api/v1/shutdown", tags=["program"])
async def shutdown_program():
    program.stop()
    logger.info("Shutting down program...")
    os.kill(os.getpid(), signal.SIGINT)
    return {"status": "ok"}


# Check status
@router.get("/api/v1/check/downloader", tags=["check"])
async def check_downloader_status():
    return check_downloader()


@router.get("/api/v1/check/rss", tags=["check"])
async def check_rss_status():
    return check_rss()


@router.get("/api/v1/check", tags=["check"])
async def check_all():
    return check_status()

