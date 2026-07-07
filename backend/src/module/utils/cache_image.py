import asyncio
import hashlib


async def save_image(img: bytes | None, suffix: str) -> str | None:
    """保存图片到本地缓存。文件写入是同步阻塞的，放到线程池中执行，避免
    在 RSS/通知等异步热路径上阻塞事件循环。"""
    if img is None:
        # Fetching the poster failed upstream; skip caching instead of
        # crashing on hashlib.md5(None).
        return None
    img_hash = hashlib.md5(img).hexdigest()[0:8]
    image_path = f"data/posters/{img_hash}.{suffix}"

    def _write() -> None:
        with open(image_path, "wb") as f:
            f.write(img)

    await asyncio.to_thread(_write)
    return f"posters/{img_hash}.{suffix}"


async def load_image(img_path: str | None) -> bytes | None:
    """读取缓存图片。文件读取是同步阻塞的，放到线程池中执行。"""
    if not img_path:
        return None

    def _read() -> bytes:
        with open(f"data/{img_path}", "rb") as f:
            return f.read()

    return await asyncio.to_thread(_read)
