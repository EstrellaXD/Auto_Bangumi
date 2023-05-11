import os
import signal
import logging
import asyncio

from .download import router

from module.core import start_thread, start_program, stop_thread, stop_event


logger = logging.getLogger(__name__)


@router.on_event("startup")
async def startup():
    await start_program()


@router.on_event("shutdown")
async def shutdown():
    stop_event.set()
    logger.info("Stopping program...")


@router.get("/api/v1/restart", tags=["program"])
async def restart():
    stop_thread()
    start_thread()
    return {"status": "ok"}


@router.get("/api/v1/start", tags=["program"])
async def start():
    start_thread()
    return {"status": "ok"}


@router.get("/api/v1/stop", tags=["program"])
async def stop():
    stop_thread()
    return {"status": "ok"}


@router.get("/api/v1/status", tags=["program"])
async def status():
    if stop_event.is_set():
        return {"status": "stop"}
    else:
        return {"status": "running"}


@router.get("/api/v1/shutdown", tags=["program"])
async def shutdown_program():
    stop_thread()
    logger.info("Shutting down program...")
    os.kill(os.getpid(), signal.SIGINT)
    return {"status": "ok"}


@router.get("/api/v1/setLog/{log_level}", tags=["program"])
async def set_log_level(log_level: str):
    if log_level == "DEBUG":
        logger.setLevel(logging.DEBUG)
        logger.debug("Log level set to DEBUG")
    elif log_level == "INFO":
        logger.setLevel(logging.INFO)
        logger.info("Log level set to INFO")
    elif log_level == "WARNING":
        logger.setLevel(logging.WARNING)
        logger.warning("Log level set to WARNING")
    elif log_level == "ERROR":
        logger.setLevel(logging.ERROR)
        logger.error("Log level set to ERROR")
    elif log_level == "CRITICAL":
        logger.setLevel(logging.CRITICAL)
        logger.critical("Log level set to CRITICAL")
    else:
        return {"status": "invalid log level"}
    return {"status": "ok"}