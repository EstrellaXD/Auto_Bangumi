import asyncio
import functools
import logging

from .timeout import timeout

logger = logging.getLogger(__name__)
_lock = asyncio.Lock()


def qb_connect_failed_wait(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        times = 0
        while times < 5:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.debug(f"URL: {args[0]}")
                logger.warning(e)
                logger.warning("Cannot connect to qBittorrent. Wait 5 min and retry...")
                await asyncio.sleep(300)
                times += 1

    return wrapper


def api_failed(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.debug(f"URL: {args[0]}")
            logger.warning("Wrong API response.")
            logger.debug(e)

    return wrapper


def locked(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        async with _lock:
            return await func(*args, **kwargs)

    return wrapper
