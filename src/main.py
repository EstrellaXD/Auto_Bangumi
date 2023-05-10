import logging
import uvicorn
import threading
import time

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from module.api import router
from module.conf import VERSION, settings, setup_logger
from module.rss import RSSAnalyser
from module.manager import Renamer
from module.conf.uvicorn_logging import logging_config


logger = logging.getLogger(__name__)
rss_link = settings.rss_link()
stop_event = threading.Event()


def show_info():
    with open("icon", "r") as f:
        for line in f.readlines():
            logger.info(line.strip("\n"))
    logger.info(
        f"Version {VERSION}  Author: EstrellaXD Twitter: https://twitter.com/Estrella_Pan"
    )
    logger.info("GitHub: https://github.com/EstrellaXD/Auto_Bangumi/")
    logger.info("Starting AutoBangumi...")


def rss_loop(stop_event, rss_link: str):
    rss_analyser = RSSAnalyser()
    while not stop_event.is_set():
        rss_analyser.run(rss_link)
        stop_event.wait(settings.program.rss_time)


def rename_loop(stop_event):
    while not stop_event.is_set():
        with Renamer() as renamer:
            renamer.rename()
        stop_event.wait(settings.program.rename_time)


rss_thread = threading.Thread(
    target=rss_loop,
    args=(stop_event, rss_link),
)

rename_thread = threading.Thread(
    target=rename_loop,
    args=(stop_event,),
)


def stop_thread():
    global rss_thread, rename_thread
    if not stop_event.is_set():
        stop_event.set()
        rename_thread.join()
        rss_thread.join()


def start_thread():
    global rss_thread, rename_thread
    if stop_event.is_set():
        stop_event.clear()
        time.sleep(1)
        settings.load()
        rss_link = settings.rss_link()
        new_level = logging.DEBUG if settings.log.debug_enable else logging.INFO
        setup_logger(new_level)
        print(new_level)
        rss_thread = threading.Thread(target=rss_loop, args=(stop_event, rss_link))
        rename_thread = threading.Thread(target=rename_loop, args=(stop_event,))
        rss_thread.start()
        rename_thread.start()
        return {"status": "ok"}


@router.on_event("startup")
async def startup():
    global rss_thread, rename_thread
    log_level = logging.DEBUG if settings.log.debug_enable else logging.INFO
    setup_logger(log_level)
    show_info()
    rss_thread.start()
    rename_thread.start()


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


if __name__ == "__main__":
    uvicorn.run(
        "main:router", host="0.0.0.0", port=settings.program.webui_port, log_config=logging_config, reload=True
    )
