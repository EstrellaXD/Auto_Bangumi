import asyncio
import functools
import logging

import httpx

logger = logging.getLogger(__name__)
_lock = asyncio.Lock()

_RETRY_DELAYS = [5, 15, 45, 120, 300]


def qb_connect_failed_wait(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        times = 0
        while times < 5:
            try:
                return await func(*args, **kwargs)
            except (
                ConnectionError,
                TimeoutError,
                OSError,
                httpx.ConnectError,
                httpx.TimeoutException,
                httpx.RequestError,
            ) as e:
                delay = _RETRY_DELAYS[times]
                logger.debug("URL: %s", args[0])
                logger.warning(e)
                logger.warning(
                    "Cannot connect to qBittorrent. Wait %ds and retry...", delay
                )
                await asyncio.sleep(delay)
                times += 1

    return wrapper


def api_failed(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.debug("URL: %s", args[0])
            logger.warning("Wrong API response.")
            logger.debug(e)

    return wrapper


def locked(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        async with _lock:
            return await func(*args, **kwargs)

    return wrapper
