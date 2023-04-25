import logging
import time

logger = logging.getLogger(__name__)


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
