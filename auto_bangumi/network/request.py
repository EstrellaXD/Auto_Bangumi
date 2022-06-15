import time

import requests
import logging

from bs4 import BeautifulSoup

from conf import settings

logger = logging.getLogger(__name__)


class RequestURL:
    def __init__(self):
        self.session = requests.session()
        if settings.http_proxy is not None:
            self.proxy = {
                "https": settings.http_proxy,
                "http": settings.http_proxy,
                "socks": settings.http_proxy
            }
        else:
            self.proxy = None
        self.header = {
            "user-agent": "Mozilla/5.0",
            "Accept": "application/xml"
        }

    def get_url(self, url):
        times = 0
        while times < 5:
            try:
                req = self.session.get(url=url, headers=self.header, proxies=self.proxy)
                return req
            except Exception as e:
                logger.debug(f"URL: {url}")
                logger.error("ERROR with DNS/Connection.")
                time.sleep(settings.connect_retry_interval)
                times += 1

    def get_content(self, url, content="xml"):
        if content == "xml":
            return BeautifulSoup(self.get_url(url).text, content)
        elif content == "json":
            return self.get_url(url).json()

    def close(self):
        self.session.close()


