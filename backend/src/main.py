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
from module.api.health import router as health_router
from module.conf import VERSION, settings, setup_logger
from module.core import AppContext
from module.mcp import create_mcp_app, create_mcp_router

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
    ctx: AppContext = app.state.ctx
    # Run migrations before serving; failure here aborts boot loudly.
    await ctx.startup()
    # 插件在迁移之后启动（插件 KV 表由迁移创建），且早于后台任务
    await ctx.plugins.start()
    # First run just created the DB — do not auto-start loops (matches the old
    # Program.startup early return); the user starts them after setup.
    if not ctx.first_run_boot:
        # start_tasks() itself schedules the downloader-wait + loop-start as a
        # supervised background task and returns immediately (CONTRACT #5),
        # so this does not block server startup.
        await ctx.start_tasks()
    yield
    # Shutdown
    await ctx.stop()
    await ctx.plugins.stop()


def create_app() -> FastAPI:
    ctx = AppContext.build(settings)
    app = FastAPI(lifespan=lifespan)
    app.state.ctx = ctx

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )

    # mount routers
    app.include_router(v1, prefix="/api")

    # unauthenticated liveness probe, mounted at the app root (not /api) so
    # it stays reachable without auth for container/orchestrator health checks
    app.include_router(health_router)

    # MCP：Streamable HTTP 在 /mcp，SSE 在 /mcp/sse
    app.include_router(create_mcp_router())
    app.mount("/mcp", create_mcp_app(ctx))

    return app


app = create_app()


_POSTERS_BASE = Path("data/posters").resolve()


@app.get("/posters/{path:path}", tags=["posters"])
def posters(path: str):
    resolved = (_POSTERS_BASE / path).resolve()
    if not str(resolved).startswith(str(_POSTERS_BASE)):
        return HTMLResponse(status_code=403)
    return FileResponse(str(resolved))


# 前端插件组件与宿主同源（第 3.8 节），只允许加载本站脚本：远程脚本与内联脚本
# 都被拒绝。只加在 SPA 文档上，/docs 的 Swagger 页面依赖内联脚本与 CDN。
_SPA_HEADERS = {"Content-Security-Policy": "script-src 'self'"}


def mount_webui(app: FastAPI, dist: Path) -> None:
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")
    app.mount("/images", StaticFiles(directory=dist / "images"), name="images")
    # 自托管 Inter 字体：index.html 以 /fonts/*.woff2 预加载，不挂载则被下面的
    # SPA 兜底路由回成 index.html，全站字体静默回退。在线更新可能覆盖进来
    # 更旧的、没有 fonts/ 的 dist，故按存在性挂载。
    if (dist / "fonts").is_dir():
        app.mount("/fonts", StaticFiles(directory=dist / "fonts"), name="fonts")
    # app.mount("/icons", StaticFiles(directory="dist/icons"), name="icons")
    templates = Jinja2Templates(directory=dist)

    # dist/ is immutable inside the container — snapshot once instead of
    # hitting the filesystem on every request.
    dist_files = frozenset(os.listdir(dist))

    @app.get("/{path:path}")
    def html(request: Request, path: str):
        if path in dist_files:
            return FileResponse(dist / path, headers=_SPA_HEADERS)
        else:
            return templates.TemplateResponse(
                request, "index.html", headers=_SPA_HEADERS
            )


if VERSION != "DEV_VERSION":
    mount_webui(app, Path("dist"))

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
