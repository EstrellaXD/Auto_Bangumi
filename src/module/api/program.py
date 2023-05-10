import os
import signal
import logging

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .proxy import router

from module.core import start_thread, start_program, stop_thread, stop_event
from module.conf import VERSION, settings, setup_logger


logger = logging.getLogger(__name__)


@router.on_event("startup")
async def startup():
    log_level = logging.DEBUG if settings.log.debug_enable else logging.INFO
    setup_logger(log_level)
    start_program()


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


if VERSION != "DEV_VERSION":
    router.mount("/assets", StaticFiles(directory="templates/assets"), name="assets")
    templates = Jinja2Templates(directory="templates")

    # HTML Response
    @router.get("/{full_path:path}", response_class=HTMLResponse, tags=["html"])
    def index(request: Request):
        context = {"request": request}
        return templates.TemplateResponse("index.html", context)
else:
    @router.get("/", status_code=302, tags=["html"])
    def index():
        return RedirectResponse("/docs")