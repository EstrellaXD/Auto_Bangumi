import time

import requests
import socket
import socks
import logging

from bs4 import BeautifulSoup

from autobangumi.conf import settings

logger = logging.getLogger(__name__)


class RequestURL:
    def __init__(self):
        self.session = requests.session()
        if settings.NETWORK["HTTP"] is not None:
            self.session.proxies = {
                "https": settings.NETWORK["HTTP"],
                "http": settings.NETWORK["HTTP"],
            }
        elif settings.NETWORK["Socks"] is not None:
            socks_info = settings.NETWORK["Socks"].split(",")
            socks.set_default_proxy(socks.SOCKS5, addr=socks_info[0], port=int(socks_info[1]), rdns=True,
                                    username=socks_info[2], password=socks_info[3])
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


