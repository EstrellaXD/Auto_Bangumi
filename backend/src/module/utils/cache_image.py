import asyncio
import hashlib
import logging

logger = logging.getLogger(__name__)


async def save_image(
    img: bytes | None, suffix: str, source_url: str | None = None
) -> str | None:
    """保存图片到本地缓存。文件写入是同步阻塞的，放到线程池中执行，避免
    在 RSS/通知等异步热路径上阻塞事件循环。

    传入 source_url 时在图片旁写一个 ``<name>.url`` sidecar 记录源地址：
    通知端（Telegram sendPhoto 等）可以直接发 URL 让服务端拉图，绕开本地
    multipart 上传（#1094）。
    """
    if img is None:
        # Fetching the poster failed upstream; skip caching instead of
        # crashing on hashlib.md5(None).
        return None
    img_hash = hashlib.md5(img).hexdigest()[0:8]
    image_path = f"data/posters/{img_hash}.{suffix}"

    def _write() -> None:
        with open(image_path, "wb") as f:
            f.write(img)
        if source_url:
            with open(f"{image_path}.url", "w", encoding="utf-8") as f:
                f.write(source_url)

    await asyncio.to_thread(_write)
    return f"posters/{img_hash}.{suffix}"


async def load_image(img_path: str | None) -> bytes | None:
    """读取缓存图片。文件读取是同步阻塞的，放到线程池中执行。
    缓存文件丢失（手动清理、迁移不完整）返回 None，不炸穿通知发送。"""
    if not img_path:
        return None

    def _read() -> bytes | None:
        try:
            with open(f"data/{img_path}", "rb") as f:
                return f.read()
        except OSError:
            logger.warning("Cached poster %s is missing or unreadable.", img_path)
            return None

    return await asyncio.to_thread(_read)


async def load_poster_url(img_path: str | None) -> str | None:
    """读取缓存图片对应的源 URL sidecar；旧缓存没有 sidecar 时返回 None。"""
    if not img_path:
        return None

    def _read() -> str | None:
        try:
            with open(f"data/{img_path}.url", encoding="utf-8") as f:
                return f.read().strip() or None
        except OSError:
            return None

    return await asyncio.to_thread(_read)
