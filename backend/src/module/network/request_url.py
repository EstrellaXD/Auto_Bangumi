import logging
import time

import httpx

from module.conf import settings

logger = logging.getLogger(__name__)


class RequestURL:
    def __init__(self):
        self.header = {"user-agent": "Mozilla/5.0", "Accept": "application/xml"}

    async def get_url(self, url, retry=3):
        try_time = 0
        while True:
            try:
                req = await self.client.get(url=url, headers=self.header, timeout=5)
                req.raise_for_status()
                return req
            except httpx.RequestError:
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
        return None

    async def post_url(self, url: str, data: dict, retry=3):
        try_time = 0
        while True:
            try:
                req = await self.client.post(
                    url=url, headers=self.header, data=data, timeout=5
                )
                req.raise_for_status()
                return req
            except httpx.RequestError:
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
        return None

    async def check_url(self, url: str):
        if "://" not in url:
            url = f"http://{url}"
        try:
            req = await self.client.get(url=url, headers=self.header, timeout=5)
            req.raise_for_status()
            return True
        except httpx.RequestError:
            logger.debug(f"[Network] Cannot connect to {url}.")
            return False

    async def post_form(self, url: str, data: dict, files):
        try:
            req = await self.client.post(
                url=url, headers=self.header, data=data, files=files, timeout=5
            )
            req.raise_for_status()
            return req
        except httpx.RequestError:
            logger.warning(f"[Network] Cannot connect to {url}.")
            return None

    async def __aenter__(self):
        proxy = None
        if settings.proxy.enable:
            auth = f"{settings.proxy.username}:{settings.proxy.password}@" \
                if settings.proxy.username else \
                ""
            if "http" in settings.proxy.type:
                proxy = f"{settings.proxy.type}://{auth}{settings.proxy.host}:{settings.proxy.port}"
            elif settings.proxy.type == "socks5":
                proxy = f"socks5://{auth}{settings.proxy.host}:{settings.proxy.port}"
            else:
                logger.error(f"[Network] Unsupported proxy type: {settings.proxy.type}")
        self.client = httpx.AsyncClient(
            http2=True,
            proxies=proxy,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
