import logging
import threading
import time

from .timeout import timeout

logger = logging.getLogger(__name__)
lock = threading.Lock()


def qb_connect_failed_wait(func):
    def wrapper(*args, **kwargs):
        times = 0
        while times < 5:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.debug(f"URL: {args[0]}")
                logger.warning(e)
                logger.warning("Cannot connect to qBittorrent. Wait 5 min and retry...")
                time.sleep(300)
                times += 1

    return wrapper


def api_failed(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.debug(f"URL: {args[0]}")
            logger.warning("Wrong API response.")
            logger.debug(e)

    return wrapper


def locked(func):
    def wrapper(*args, **kwargs):
        with lock:
            return func(*args, **kwargs)

    return wrapper
