import time

import requests
import socket
import socks
import logging

from module.conf import settings

logger = logging.getLogger(__name__)


class RequestURL:
    def __init__(self):
        self.header = {
            "user-agent": "Mozilla/5.0",
            "Accept": "application/xml"
        }

    def get_url(self, url):
        try_time = 0
        while try_time < 5:
            try:
                req = self.session.get(url=url, headers=self.header)
                req.raise_for_status()
                return req
            except requests.RequestException as e:
                logger.debug(f"URL: {url}")
                logger.debug(e)
                logger.warning("ERROR with Connection.Please check DNS/Connection settings")
                time.sleep(5)
                try_time += 1
            except Exception as e:
                logger.debug(f"URL: {url}")
                logger.debug(e)
                break

    def post_url(self, url: str, data: dict):
        try_time = 0
        while try_time < 5:
            try:
                req = self.session.post(url=url, headers=self.header, data=data)
                req.raise_for_status()
                return req
            except requests.RequestException as e:
                logger.debug(f"URL: {url}")
                logger.debug(e)
                logger.warning("ERROR with Connection.Please check DNS/Connection settings")
                time.sleep(5)
                try_time += 1
            except Exception as e:
                logger.debug(f"URL: {url}")
                logger.debug(e)
                break

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
                socks.set_default_proxy(socks.SOCKS5, addr=settings.proxy.host, port=settings.proxy.port, rdns=True,
                                        username=settings.proxy.username, password=settings.proxy.password)
                socket.socket = socks.socksocket
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()


