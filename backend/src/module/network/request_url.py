import asyncio
import logging
import time

import httpx

from module.conf import settings

logger = logging.getLogger(__name__)


def retry_async(times=3):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            url = kwargs.get("url", None)
            if url is None:
                url = args[0]
            for _ in range(times):
                try:
                    resp = await func(*args, **kwargs)
                    logger.debug(f"[Network] Successfully connected to {url}")
                    return resp
                except httpx.RequestError:
                    if _ < times - 1:
                        await asyncio.sleep(5)  # 延迟5秒后重试
                    logger.warning(
                        f"[Network] Cannot connect to {url}. Wait for 5 seconds."
                    )
                except Exception as e:
                    logger.debug(e)
                    logger.error(f"[Network] Failed connecting to {url}")
                    logger.warning("[Network] Please check DNS/Connection settings")
                    break
            return None

        return wrapper

    return decorator


class RequestURL:
    def __init__(self):
        self.header = {"user-agent": "Mozilla/5.0", "Accept": "application/xml"}

    @retry_async()
    async def get_url(self, url):
        req = await self.client.get(url=url)
        req.raise_for_status()
        return req

    @retry_async()
    async def post_url(self, url: str, data: dict):
        req = await self.client.post(url=url, data=data)
        req.raise_for_status()
        return req

    async def check_url(self, url: str):
        if "://" not in url:
            url = f"http://{url}"
        try:
            req = await self.client.get(url=url)
            req.raise_for_status()
            return True
        except httpx.RequestError:
            logger.debug(f"[Network] Cannot connect to {url}.")
            return False

    async def post_form(self, url: str, data: dict, files):
        try:
            req = await self.client.post(url=url, data=data, files=files)
            req.raise_for_status()
            return req
        except httpx.RequestError:
            logger.warning(f"[Network] Cannot connect to {url}.")
            return None

    async def __aenter__(self):
        proxy = None
        if settings.proxy.enable:
            auth = (
                f"{settings.proxy.username}:{settings.proxy.password}@"
                if settings.proxy.username
                else ""
            )
            if "http" in settings.proxy.type:
                proxy = f"{settings.proxy.type}://{auth}{settings.proxy.host}:{settings.proxy.port}"
            elif settings.proxy.type == "socks5":
                proxy = f"socks5://{auth}{settings.proxy.host}:{settings.proxy.port}"
            else:
                logger.error(f"[Network] Unsupported proxy type: {settings.proxy.type}")
        self.client = httpx.AsyncClient(
            http2=True, proxies=proxy, headers=self.header, timeout=5
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
