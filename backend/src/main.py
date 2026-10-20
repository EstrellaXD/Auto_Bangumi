import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import anyio
import uvicorn
from anyio.abc import TaskGroup, TaskStatus
from fastapi import APIRouter, Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send

from module.api import v1
from module.api.health import router as health_router
from module.conf import VERSION, settings, setup_logger
from module.core import AppContext
from module.mcp.security import McpAccessMiddleware

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
    # 子应用不会运行自己的 lifespan，MCP 会话管理器在这里提供的任务组里运行
    async with app.state.mcp.running():
        yield
    # Shutdown
    await ctx.stop()
    await ctx.plugins.stop()


class _LazyMcpApp:
    """首个通过访问控制的 /mcp 请求才导入 mcp 库、构建子应用并启动会话管理器。

    多数用户不用 MCP，启动时不加载可省约 20 MB 内存。会话管理器的 run() 内含
    anyio 任务组，必须在同一个任务里进出，所以它跑在 lifespan 持有的任务组里，
    关停时随任务组取消。
    """

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx
        self._tasks: TaskGroup | None = None
        self._app: ASGIApp | None = None
        # 并发的首批请求只构建一次
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def running(self) -> AsyncIterator[None]:
        async with anyio.create_task_group() as tasks:
            self._tasks = tasks
            yield
            tasks.cancel_scope.cancel()
        # 每次 create_mcp_app 都新建会话管理器，再次启动时重新构建
        self._tasks = self._app = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self._app is None:
            async with self._lock:
                if self._app is None:
                    self._app = await self._build()
        await self._app(scope, receive, send)

    async def _build(self) -> ASGIApp:
        if self._tasks is None:
            raise RuntimeError("MCP 只能在应用 lifespan 运行期间使用")
        from module.mcp import create_mcp_app, mcp

        app = create_mcp_app(self._ctx)
        manager = mcp.session_manager

        async def serve(
            *, task_status: TaskStatus[None] = anyio.TASK_STATUS_IGNORED
        ) -> None:
            async with manager.run():
                task_status.started()
                await anyio.sleep_forever()

        await self._tasks.start(serve)
        return app


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

    # SSE（text/event-stream）由中间件默认排除，不会被压缩缓冲
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # mount routers
    app.include_router(v1, prefix="/api")

    # unauthenticated liveness probe, mounted at the app root (not /api) so
    # it stays reachable without auth for container/orchestrator health checks
    app.include_router(health_router)

    # MCP 服务（Streamable HTTP）：用路由而不是 mount，端点才是 /mcp 本身
    # （mount 只匹配 /mcp/...，/mcp 会被 307 重定向到 /mcp/）。访问控制在
    # 延迟构建之前，被拒的请求不会加载 mcp 库
    app.state.mcp = _LazyMcpApp(ctx)
    app.router.routes.append(Route("/mcp", endpoint=McpAccessMiddleware(app.state.mcp)))

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
def _spa_headers(request: Request, response: Response) -> None:
    response.headers["Content-Security-Policy"] = "script-src 'self'"
    # 入口 HTML（含回落到 index.html 的前端路由深链接，即末段无扩展名的路径）
    # 必须每次校验，否则会引用已不存在的旧哈希文件；assets/ 下的文件名带内容
    # 哈希，可永久缓存。fonts/、images/ 等不带哈希，不设置。只看路径段，
    # 带 root_path 前缀时同样适用。
    path = request.url.path
    last = path.rsplit("/", 1)[-1]
    if "." not in last or last.endswith(".html"):
        response.headers["Cache-Control"] = "no-cache"
    elif "/assets/" in path:
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"


def mount_webui(app: FastAPI, dist: Path) -> None:
    # 前端路由优先级最低，只在没有路径操作或挂载匹配时生效；浏览器导航
    # （Accept: text/html）到不存在的路径时回落到 index.html，其它请求返回 404
    web = APIRouter(dependencies=[Depends(_spa_headers)])
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
