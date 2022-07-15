import time

import requests
import socket
import socks
import logging

from bs4 import BeautifulSoup

from conf import settings

logger = logging.getLogger(__name__)


class RequestURL:
    def __init__(self):
        self.session = requests.session()
        if settings.http_proxy is not None:
            self.session.proxies = {
                "https": settings.http_proxy,
                "http": settings.http_proxy,
            }
        elif settings.socks is not None:
            socks_info = settings.socks.split(",")
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
                logger.warning("ERROR with DNS/Connection.")
                time.sleep(settings.connect_retry_interval)
                times += 1

    def get_content(self, url, content="xml"):
        if content == "xml":
            return BeautifulSoup(self.get_url(url).text, content)
        elif content == "json":
            return self.get_url(url).json()

    def close(self):
        self.session.close()


if __name__ == "__main__":
    a = RequestURL()
    socks.set_default_proxy(socks.SOCKS5, "192.168.30.2", 19990, True, username="abc", password="abc")
    socket.socket = socks.socksocket
    b = a.get_url('https://www.themoviedb.org').text
    print(b)


