import signal
import logging
import os

from fastapi import HTTPException, status, Depends
from fastapi import FastAPI

from module.core import Program
from module.security import get_current_user

logger = logging.getLogger(__name__)
program = Program()
router = FastAPI()


@router.on_event("startup")
async def startup():
    program.startup()


@router.on_event("shutdown")
async def shutdown():
    program.stop()


@router.get("/api/v1/restart", tags=["program"])
async def restart(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    try:
        program.restart()
        return {"status": "ok"}
    except Exception as e:
        logger.debug(e)
        logger.warning("Failed to restart program")
        raise HTTPException(status_code=500, detail="Failed to restart program")


@router.get("/api/v1/start", tags=["program"])
async def start(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    try:
        program.start()
        return {"status": "ok"}
    except Exception as e:
        logger.debug(e)
        logger.warning("Failed to start program")
        raise HTTPException(status_code=500, detail="Failed to start program")


@router.get("/api/v1/stop", tags=["program"])
async def stop(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    program.stop()
    return {"status": "ok"}


@router.get("/api/v1/status", tags=["program"])
async def status(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    if not program.is_running:
        return {"status": "stop"}
    else:
        return {"status": "running"}


@router.get("/api/v1/shutdown", tags=["program"])
async def shutdown_program(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    program.stop()
    logger.info("Shutting down program...")
    os.kill(os.getpid(), signal.SIGINT)
    return {"status": "ok"}


# Check status
@router.get("/api/v1/check/downloader", tags=["check"])
async def check_downloader_status(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    return program.check_downloader()


@router.get("/api/v1/check/rss", tags=["check"])
async def check_rss_status(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    return program.check_analyser()
