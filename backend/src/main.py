import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from module.api import v1
from module.api.program import program
from module.conf import VERSION, settings, setup_logger
from module.mcp import create_mcp_app

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    # Startup
    asyncio.create_task(program.startup())
    yield
    # Shutdown
    await program.stop()


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )

    # mount routers
    app.include_router(v1, prefix="/api")

    # mount MCP server (SSE transport for LLM tool integration)
    app.mount("/mcp", create_mcp_app())

    return app


app = create_app()


_POSTERS_BASE = Path("data/posters").resolve()


@app.get("/posters/{path:path}", tags=["posters"])
def posters(path: str):
    resolved = (_POSTERS_BASE / path).resolve()
    if not str(resolved).startswith(str(_POSTERS_BASE)):
        return HTMLResponse(status_code=403)
    return FileResponse(str(resolved))


if VERSION != "DEV_VERSION":
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")
    app.mount("/images", StaticFiles(directory="dist/images"), name="images")
    # app.mount("/icons", StaticFiles(directory="dist/icons"), name="icons")
    templates = Jinja2Templates(directory="dist")

    # dist/ is immutable inside the container — snapshot once instead of
    # hitting the filesystem on every request.
    _DIST_FILES = frozenset(os.listdir("dist"))

    @app.get("/{path:path}")
    def html(request: Request, path: str):
        if path in _DIST_FILES:
            return FileResponse(f"dist/{path}")
        else:
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
        host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(
        app,
        host=host,
        port=settings.program.webui_port,
        log_config=uvicorn_logging_config,
    )
