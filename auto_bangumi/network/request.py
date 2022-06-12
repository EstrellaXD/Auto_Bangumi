import time

import requests
import logging

from bs4 import BeautifulSoup

from conf import settings

logger = logging.getLogger(__name__)


class RequestsURL:
    def __init__(self):
        self.session = requests.session()
        if settings.http_proxy is not None:
            self.proxy = {
                "https": settings.http_proxy,
                "http": settings.http_proxy
            }
        else:
            self.proxy = None

    def get_url(self, url):
        times = 1
        while times < 5:
            try:
                req = self.session.get(url, proxies=self.proxy)
                return BeautifulSoup(req.text, "xml")
            except Exception:
                # logger.exception(e)
                logger.error("ERROR with DNS/Connection.")
                time.sleep(settings.connect_retry_interval)
                times += 1

    def close(self):
        self.session.close()


if __name__ == "__main__":
    network_req = RequestsURL()
    req = network_req.get_url("https://mikanani.me/RSS/Classic")
    print(req.find_all("item"))
    network_req.close()
    req = network_req.get_url("https://mikanani.me/RSS/Classic")
    print(req.find_all("item"))