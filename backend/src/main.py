import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from starlette.routing import Route

from module.api import v1
from module.api.health import router as health_router
from module.conf import VERSION, settings, setup_logger
from module.core import AppContext
from module.mcp import create_mcp_app, mcp

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
    # 子应用不会运行自己的 lifespan，MCP 会话管理器在这里启动
    async with app.state.mcp_sessions.run():
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

    # MCP 服务（Streamable HTTP）：用路由而不是 mount，端点才是 /mcp 本身
    # （mount 只匹配 /mcp/...，/mcp 会被 307 重定向到 /mcp/）
    app.router.routes.append(Route("/mcp", endpoint=create_mcp_app(ctx)))
    # 每次 create_mcp_app 都新建会话管理器，记下本应用的这一个供 lifespan 运行
    app.state.mcp_sessions = mcp.session_manager

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
# 都被拒绝。只加在前端静态文件上，/docs 的 Swagger 页面依赖内联脚本与 CDN。
def _spa_csp(response: Response) -> None:
    response.headers["Content-Security-Policy"] = "script-src 'self'"


def mount_webui(app: FastAPI, dist: Path) -> None:
    # 前端路由优先级最低，只在没有路径操作或挂载匹配时生效；浏览器导航
    # （Accept: text/html）到不存在的路径时回落到 index.html，其它请求返回 404
    web = APIRouter(dependencies=[Depends(_spa_csp)])
    web.frontend("/", directory=dist)
    app.include_router(web)


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
        # 原生 SSE 没有关停监听，常开的事件流会让退出一直等到浏览器断开；
        # 限定等待时间，/shutdown 与在线更新的重启才能按时完成
        timeout_graceful_shutdown=5,
    )
