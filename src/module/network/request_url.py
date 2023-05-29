import time

import requests
import socket
import socks
import logging

from module.conf import settings

logger = logging.getLogger(__name__)


class RequestURL:
    def __init__(self):
        self.header = {"user-agent": "Mozilla/5.0", "Accept": "application/xml"}

    def get_url(self, url, retry=3):
        try_time = 0
        while True:
            try:
                req = self.session.get(url=url, headers=self.header, timeout=5)
                req.raise_for_status()
                return req
            except requests.RequestException:
                logger.warning(f"[Network] Cannot connect to {url}. Wait for 5 seconds.")
                try_time += 1
                if try_time >= retry:
                    break
                time.sleep(5)
            except Exception as e:
                logger.debug(e)
                break
        logger.error(f"[Network] Failed connecting to {url}")
        logger.warning("[Network] Please check DNS/Connection settings")
        raise ConnectionError(f"Failed connecting to {url}")

    def post_url(self, url: str, data: dict, retry=3):
        try_time = 0
        while True:
            try:
                req = self.session.post(
                    url=url, headers=self.header, data=data, timeout=5
                )
                req.raise_for_status()
                return req
            except requests.RequestException:
                logger.warning(f"[Network] Cannot connect to {url}. Wait for 5 seconds.")
                try_time += 1
                if try_time >= retry:
                    break
                time.sleep(5)
            except Exception as e:
                logger.debug(e)
                break
        logger.error(f"[Network] Failed connecting to {url}")
        logger.warning("[Network] Please check DNS/Connection settings")
        raise ConnectionError(f"Failed connecting to {url}")

    def check_url(self, url: str):
        if "://" not in url:
            url = f"http://{url}"
        try:
            req = requests.head(url=url, headers=self.header, timeout=5)
            req.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.debug(f"Cannot connect to {url}.")
            return False

    def __enter__(self):
        self.session = requests.Session()
        if settings.proxy.enable:
            if settings.proxy.type == "http":
                url = f"http://{settings.proxy.host}:{settings.proxy.port}"
                self.session.proxies = {
                    "https": url,
                    "http": url,
                }
            elif settings.proxy.type == "socks5":
                socks.set_default_proxy(
                    socks.SOCKS5,
                    addr=settings.proxy.host,
                    port=settings.proxy.port,
                    rdns=True,
                    username=settings.proxy.username,
                    password=settings.proxy.password,
                )
                socket.socket = socks.socksocket
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
