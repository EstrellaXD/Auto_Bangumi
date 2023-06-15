import logging

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from module.api import v1
from module.api.proxy import router as proxy_router
from module.conf import settings, setup_logger
from starlette.types import ASGIApp

setup_logger(reset=True)
logger = logging.getLogger(__name__)
uvicorn_logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": logger.handlers,
    "loggers": {
        "uvicorn": {
            "level": logger.level,
        },
        "uvicorn.access": {
            "level": "WARNING",
        },
    },
}


def mount_dist(app: ASGIApp):
    from module.conf import VERSION

    if VERSION != "DEV_VERSION":
        app.mount("/", StaticFiles(directory="dist", html=True), name="dist")
        templates = Jinja2Templates(directory="dist")
        @app.get("/", response_class=HTMLResponse, tags=["html"])
        def index(request: Request):
            return templates.TemplateResponse("index.html", {"request": request})
    else:
        @app.get("/", status_code=302, tags=["html"])
        def index():
            return RedirectResponse("/docs")

def create_app() -> ASGIApp:
    app = FastAPI()

    # mount dist
    mount_dist(app)

    # mount router
    app.include_router(proxy_router)
    app.include_router(v1, prefix="/api")

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.program.webui_port,
        log_config=uvicorn_logging_config,
    )
