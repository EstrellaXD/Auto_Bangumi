import time

import requests
import socket
import socks
import logging

from bs4 import BeautifulSoup

from module.conf import settings

logger = logging.getLogger(__name__)


class RequestURL:
    def __init__(self):
        self.session = requests.session()
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
        self.header = {
            "user-agent": "Mozilla/5.0",
            "Accept": "application/xml"
        }

    def get_url(self, url):
        times = 0
        while times < 5:
            try:
                req = self.session.get(url=url, headers=self.header)
                return req
            except Exception as e:
                logger.debug(f"URL: {url}")
                logger.debug(e)
                logger.warning("ERROR with Connection.Please check DNS/Connection settings")
                time.sleep(5)
                times += 1

    def get_content(self, url, content="xml"):
        if content == "xml":
            return BeautifulSoup(self.get_url(url).text, content)
        elif content == "json":
            return self.get_url(url).json()

    def close(self):
        self.session.close()


