import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from module.api import lifespan, v1
from module.conf import VERSION, settings, setup_logger

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
    app = FastAPI(lifespan=lifespan)
    # mount routers
    app.include_router(v1, prefix="/api")
    return app


app = create_app()
if VERSION != "DEV_VERSION":
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")
    app.mount("/images", StaticFiles(directory="dist/images"), name="images")
    templates = Jinja2Templates(directory="dist")

    @app.get("/{path:path}")
    async def serve_spa(request: Request, path: str):
        """
        安全的SPA静态文件服务
        - 防止路径遍历攻击
        - 限制只能访问dist目录下的文件
        - 对未匹配路由返回SPA入口页面
        """
        # 空路径或根路径，返回SPA入口页面
        if not path or path == "/":
            context = {"request": request}
            return templates.TemplateResponse("index.html", context)

        # 验证路径安全性 - 阻止路径遍历
        if ".." in path or path.startswith("/") or "\\" in path:
            logger.warning(f"[Static] Blocked path traversal attempt: {path}")
            context = {"request": request}
            return templates.TemplateResponse("index.html", context)

        # 构建安全的文件路径
        dist_dir = Path("dist").resolve()
        file_path = (dist_dir / path).resolve()

        # 确保解析后的路径仍在预期目录内
        try:
            file_path.relative_to(dist_dir)
        except ValueError:
            logger.warning(f"[Static] Path outside allowed directory: {path}")
            context = {"request": request}
            return templates.TemplateResponse("index.html", context)

        # 如果文件存在且是文件，则返回
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        else:
            # 文件不存在，返回SPA入口页面（用于客户端路由）
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
