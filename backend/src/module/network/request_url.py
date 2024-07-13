import logging
import socket
import time

import requests
import socks

from module.conf import settings

logger = logging.getLogger(__name__)


class RequestURL:
    def __init__(self):
        self.header = {"user-agent": "Mozilla/5.0", "Accept": "application/xml"}
        self._socks5_proxy = False
    
    # Patch the health api endpoint if Network connection was failed
    def change_health_status(self,health_status):
        health_check_url = "http://localhost:7892/api/v1/health"
        payload = {
            "status": health_status
        }
    
        try:
            response = requests.patch(health_check_url, json=payload)
            response.raise_for_status()
            logger.debug(
                    f"[Health] Health status changed to {health_status}."
                )
        except requests.exceptions.RequestException as e:
            logger.debug(
                    f"[Health] Failed to update health status: {e}"
                )           

    def get_url(self, url, retry=3):
        try_time = 0
        while True:
            try:
                req = self.session.get(url=url, headers=self.header, timeout=5)
                logger.debug(f"[Network] Successfully connected to {url}. Status: {req.status_code}")
                req.raise_for_status()
                self.change_health_status("healthy")
                return req
            except requests.RequestException:
                logger.debug(
                    f"[Network] Cannot connect to {url}. Wait for 5 seconds."
                )
                try_time += 1
                if try_time >= retry:
                    break
                time.sleep(5)
            except Exception as e:
                logger.debug(e)
                break
        logger.error(f"[Network] Unable to connect to {url}, Please check your network settings")
        self.change_health_status("unhealthy")
        return None

    def post_url(self, url: str, data: dict, retry=3):
        try_time = 0
        while True:
            try:
                req = self.session.post(
                    url=url, headers=self.header, data=data, timeout=5
                )
                req.raise_for_status()
                self.change_health_status("healthy")
                return req
            except requests.RequestException:
                logger.warning(
                    f"[Network] Cannot connect to {url}. Wait for 5 seconds."
                )
                try_time += 1
                if try_time >= retry:
                    break
                time.sleep(5)
            except Exception as e:
                logger.debug(e)
                break
        logger.error(f"[Network] Failed connecting to {url}")
        logger.warning("[Network] Please check DNS/Connection settings")
        self.change_health_status("unhealthy")
        return None

    def check_url(self, url: str):
        if "://" not in url:
            url = f"http://{url}"
        try:
            req = requests.head(url=url, headers=self.header, timeout=5)
            req.raise_for_status()
            return True
        except requests.RequestException:
            logger.debug(f"[Network] Cannot connect to {url}.")
            return False

    def post_form(self, url: str, data: dict, files):
        try:
            req = self.session.post(
                url=url, headers=self.header, data=data, files=files, timeout=5
            )
            req.raise_for_status()
            return req
        except requests.RequestException:
            logger.warning(f"[Network] Cannot connect to {url}.")
            return None

    def __enter__(self):
        self.session = requests.Session()
        if settings.proxy.enable:
            if "http" in settings.proxy.type:
                if settings.proxy.username:
                    username=settings.proxy.username
                    password=settings.proxy.password
                    url = f"http://{username}:{password}@{settings.proxy.host}:{settings.proxy.port}"
                    self.session.proxies = {
                        "http": url,
                        "https": url,
                    }
                else:
                    url = f"http://{settings.proxy.host}:{settings.proxy.port}"
                    self.session.proxies = {
                        "http": url,
                        "https": url,
                    }
            elif settings.proxy.type == "socks5":
                self._socks5_proxy = True
                socks.set_default_proxy(
                    socks.SOCKS5,
                    addr=settings.proxy.host,
                    port=settings.proxy.port,
                    rdns=True,
                    username=settings.proxy.username,
                    password=settings.proxy.password,
                )
                socket.socket = socks.socksocket
            else:
                logger.error(f"[Network] Unsupported proxy type: {settings.proxy.type}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._socks5_proxy:
            socks.set_default_proxy()
            socket.socket = socks.socksocket
            self._socks5_proxy = False
        self.session.close()
