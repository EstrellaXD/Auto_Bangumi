import os
import logging

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from module.api import v1
from module.api.proxy import router as proxy_router
from module.conf import settings, setup_logger, VERSION
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


def create_app() -> FastAPI:
    app = FastAPI()

    # mount routers
    app.include_router(v1, prefix="/api")
    app.include_router(proxy_router)

    return app


app = create_app()


if VERSION != "DEV_VERSION":
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")
    # app.mount("/pwa", StaticFiles(directory="dist/pwa"), name="pwa")
    # app.mount("/icons", StaticFiles(directory="dist/icons"), name="icons")
    templates = Jinja2Templates(directory="dist")

    # Resource
    @app.get("/favicon.svg", tags=["html"])
    def favicon():
        return FileResponse("dist/favicon.svg")

    @app.get("/AutoBangumi.svg", tags=["html"])
    def logo():
        return FileResponse("dist/AutoBangumi.svg")

    @app.get("/favicon-light.svg", tags=["html"])
    def favicon_light():
        return FileResponse("dist/favicon-light.svg")

    @app.get("/robots.txt", tags=["html"])
    def robots():
        return FileResponse("dist/robots.txt")

    # HTML Response
    @app.get("/{full_path:path}", response_class=HTMLResponse, tags=["html"])
    def index(request: Request):
        context = {"request": request}
        return templates.TemplateResponse("index.html", context)

else:

    @app.get("/", status_code=302, tags=["html"])
    def index():
        return RedirectResponse("/docs")


if __name__ == "__main__":
    if os.getenv("IPV6"):
        host = "::"
    else:
        host = "0.0.0.0"
    uvicorn.run(
        app,
        host=host,
        port=settings.program.webui_port,
        log_config=uvicorn_logging_config,
    )
