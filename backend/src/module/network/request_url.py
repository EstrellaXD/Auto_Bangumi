import asyncio
import logging

import httpx
from httpx_socks import AsyncProxyTransport

from module.conf import settings

logger = logging.getLogger(__name__)


class RequestURL:
    def __init__(self):
        self.header = {"user-agent": "Mozilla/5.0", "Accept": "application/xml"}
        self._client: httpx.AsyncClient | None = None

    async def get_url(self, url, retry=3):
        try_time = 0
        while True:
            try:
                req = await self._client.get(url=url, headers=self.header)
                logger.debug(f"[Network] Successfully connected to {url}. Status: {req.status_code}")
                req.raise_for_status()
                return req
            except httpx.HTTPStatusError:
                logger.debug(f"[Network] HTTP error from {url}.")
                break
            except httpx.RequestError:
                logger.debug(
                    f"[Network] Cannot connect to {url}. Wait for 5 seconds."
                )
                try_time += 1
                if try_time >= retry:
                    break
                await asyncio.sleep(5)
            except Exception as e:
                logger.debug(e)
                break
        logger.error(f"[Network] Unable to connect to {url}, Please check your network settings")
        return None

    async def post_url(self, url: str, data: dict, retry=3):
        try_time = 0
        while True:
            try:
                req = await self._client.post(
                    url=url, headers=self.header, data=data
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
                await asyncio.sleep(5)
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
            req = await self._client.head(url=url, headers=self.header)
            req.raise_for_status()
            return True
        except (httpx.RequestError, httpx.HTTPStatusError):
            logger.debug(f"[Network] Cannot connect to {url}.")
            return False

    async def post_form(self, url: str, data: dict, files):
        try:
            req = await self._client.post(
                url=url, headers=self.header, data=data, files=files
            )
            req.raise_for_status()
            return req
        except (httpx.RequestError, httpx.HTTPStatusError):
            logger.warning(f"[Network] Cannot connect to {url}.")
            return None

    async def __aenter__(self):
        timeout = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=10.0)
        if settings.proxy.enable:
            if "http" in settings.proxy.type:
                if settings.proxy.username:
                    username = settings.proxy.username
                    password = settings.proxy.password
                    proxy_url = f"http://{username}:{password}@{settings.proxy.host}:{settings.proxy.port}"
                else:
                    proxy_url = f"http://{settings.proxy.host}:{settings.proxy.port}"
                self._client = httpx.AsyncClient(proxy=proxy_url, timeout=timeout)
            elif settings.proxy.type == "socks5":
                if settings.proxy.username:
                    socks_url = f"socks5://{settings.proxy.username}:{settings.proxy.password}@{settings.proxy.host}:{settings.proxy.port}"
                else:
                    socks_url = f"socks5://{settings.proxy.host}:{settings.proxy.port}"
                transport = AsyncProxyTransport.from_url(socks_url, rdns=True)
                self._client = httpx.AsyncClient(transport=transport, timeout=timeout)
            else:
                logger.error(f"[Network] Unsupported proxy type: {settings.proxy.type}")
                self._client = httpx.AsyncClient(timeout=timeout)
        else:
            self._client = httpx.AsyncClient(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
            self._client = None
