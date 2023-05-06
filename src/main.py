import os
import signal
import logging
import uvicorn
import multiprocessing

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from module import app
from module.api import router
from module.conf import VERSION, settings


logger = logging.getLogger(__name__)

main_process = multiprocessing.Process(target=app.run, args=(settings,))


@router.on_event("startup")
async def startup():
    global main_process
    main_process.start()


@router.on_event("shutdown")
async def shutdown():
    global main_process
    if main_process.is_alive():
        os.kill(main_process.pid, signal.SIGTERM)


@router.get("/api/v1/restart", tags=["program"])
async def restart():
    global main_process
    if main_process.is_alive():
        os.kill(main_process.pid, signal.SIGTERM)
        logger.info("Restarting...")
    else:
        logger.info("Starting...")
    settings.reload()
    main_process = multiprocessing.Process(target=app.run, args=(settings,))
    main_process.start()
    logger.info("Restarted")
    return {"status": "success"}


@router.get("/api/v1/stop", tags=["program"])
async def stop():
    global main_process
    if not main_process.is_alive():
        return {"status": "failed", "reason": "Already stopped"}
    logger.info("Stopping...")
    os.kill(main_process.pid, signal.SIGTERM)
    logger.info("Stopped")
    return {"status": "success"}


@router.get("/api/v1/start", tags=["program"])
async def start():
    global main_process
    if main_process.is_alive():
        return {"status": "failed", "reason": "Already started"}
    logger.info("Starting...")
    settings.reload()
    main_process = multiprocessing.Process(target=app.run, args=(settings,))
    main_process.start()
    logger.info("Started")
    return {"status": "success"}


@router.get("/api/v1/status", tags=["program"])
async def status():
    global main_process
    if main_process.is_alive():
        return True
    else:
        return False


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
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"][
        "fmt"
    ] = "[%(asctime)s] %(levelname)-8s  %(message)s"
    uvicorn.run(
        router, host="0.0.0.0", port=settings.program.webui_port, log_config=log_config
    )
