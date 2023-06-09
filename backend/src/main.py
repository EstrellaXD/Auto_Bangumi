import logging

import uvicorn
from fastapi import FastAPI
from module.api import v1
from module.api.proxy import router as proxy_router
from module.api.web import router as web_router
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


def create_app() -> ASGIApp:
    app = FastAPI()

    # mount routers
    app.include_router(web_router)
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
