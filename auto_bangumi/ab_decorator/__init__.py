import logging
import time

import requests

from conf import settings


logger = logging.getLogger(__name__)


def qb_connect_failed_wait(func):
    def wrapper(*args, **kwargs):
        times = 0
        while times < 5:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.debug(f"URL: {args[0]}")
                logger.warning("Cannot connect to qBittorrent. Wait 5 min and retry...")
                time.sleep(3)
                times += 1
    return wrapper
