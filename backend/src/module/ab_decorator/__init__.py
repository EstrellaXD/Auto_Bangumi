import asyncio
import functools
import logging

import httpx

logger = logging.getLogger(__name__)
_lock = asyncio.Lock()

_RETRY_DELAYS = [0.5, 1, 1.5, 2, 3]


def qb_connect_failed_wait(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        times = 0
        last_error: Exception | None = None
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
                last_error = e
                delay = _RETRY_DELAYS[times]
                logger.debug("URL: %s", args[0])
                logger.warning(e)
                logger.warning(
                    "Cannot connect to qBittorrent. Wait %.1fs and retry...", delay
                )
                await asyncio.sleep(delay)
                times += 1
        # Retries exhausted: re-raise instead of silently returning None,
        # which crashed callers with a much more confusing error further down.
        logger.error("Cannot connect to qBittorrent after %d retries.", times)
        assert last_error is not None, "loop always sets last_error before exiting"
        raise last_error

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
