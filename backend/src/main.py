import logging
import os
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from module.api import lifespan, v1
from module.conf import VERSION, settings, setup_logger
from module.network import load_image
from module.security.api import get_current_user

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


@app.get("/posters/{path:path}", dependencies=[Depends(get_current_user)])
async def get_poster(path: str):
    """
    安全的poster图片访问端点
    - 添加了用户鉴权
    - 防止路径遍历攻击
    - 限制只能访问posters目录下的文件
    """
    # 验证路径安全性 - 阻止路径遍历
    if ".." in path or path.startswith("/") or "\\" in path:
        logger.warning(f"[Poster] Blocked path traversal attempt: {path}")
        raise HTTPException(status_code=400, detail="Invalid path")

    # 构建安全的文件路径
    poster_dir = Path("data/posters")
    post_path = poster_dir / Path(path)

    # 确保解析后的路径仍在预期目录内
    try:
        post_path.resolve().relative_to(poster_dir.resolve())
    except ValueError:
        logger.warning(f"[Poster] Path outside allowed directory: {path}")
        raise HTTPException(status_code=400, detail="Path outside allowed directory")

    # 如果文件不存在，尝试下载
    if not post_path.exists():
        try:
            await load_image(path)
        except Exception as e:
            logger.warning(f"[Poster] Failed to load image {path}: {e}")

    # 返回文件
    if post_path.exists() and post_path.is_file():
        return FileResponse(
            post_path,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"},  # 缓存1天
        )
    else:
        logger.warning(f"[Poster] File not found: {post_path}")
        raise HTTPException(status_code=404, detail="Poster not found")


if VERSION != "DEV_VERSION":
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")
    app.mount("/images", StaticFiles(directory="dist/images"), name="images")
    templates = Jinja2Templates(directory="dist")

    @app.get("/{path:path}")
    def html(request: Request, path: str):
        files = os.listdir("dist")
        if path in files:
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
