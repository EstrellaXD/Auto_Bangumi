import asyncio
import logging

import httpx
from httpx_socks import AsyncProxyTransport

from module.conf import settings

logger = logging.getLogger(__name__)

# Module-level shared client for connection reuse
_shared_client: httpx.AsyncClient | None = None
_shared_client_proxy_key: str | None = None


def _proxy_config_key() -> str:
    if settings.proxy.enable:
        return f"{settings.proxy.type}:{settings.proxy.host}:{settings.proxy.port}:{settings.proxy.username}"
    return ""


async def get_shared_client() -> httpx.AsyncClient:
    global _shared_client, _shared_client_proxy_key
    current_key = _proxy_config_key()
    if _shared_client is not None and _shared_client_proxy_key == current_key:
        return _shared_client
    if _shared_client is not None:
        await _shared_client.aclose()
    timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
    if settings.proxy.enable:
        if "http" in settings.proxy.type:
            if settings.proxy.username:
                proxy_url = f"http://{settings.proxy.username}:{settings.proxy.password}@{settings.proxy.host}:{settings.proxy.port}"
            else:
                proxy_url = f"http://{settings.proxy.host}:{settings.proxy.port}"
            _shared_client = httpx.AsyncClient(proxy=proxy_url, timeout=timeout)
        elif settings.proxy.type == "socks5":
            if settings.proxy.username:
                socks_url = f"socks5://{settings.proxy.username}:{settings.proxy.password}@{settings.proxy.host}:{settings.proxy.port}"
            else:
                socks_url = f"socks5://{settings.proxy.host}:{settings.proxy.port}"
            transport = AsyncProxyTransport.from_url(socks_url, rdns=True)
            _shared_client = httpx.AsyncClient(transport=transport, timeout=timeout)
        else:
            _shared_client = httpx.AsyncClient(timeout=timeout)
    else:
        _shared_client = httpx.AsyncClient(timeout=timeout)
    _shared_client_proxy_key = current_key
    return _shared_client


class RequestURL:
    # More complete User-Agent to avoid Cloudflare blocking
    DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def __init__(self):
        self.header = {"User-Agent": self.DEFAULT_UA, "Accept": "application/xml"}
        self._client: httpx.AsyncClient | None = None

    def _get_headers(self, url: str) -> dict:
        """Get appropriate headers based on URL type."""
        base_headers = {
            "User-Agent": self.DEFAULT_UA,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        # For torrent files, use different Accept header
        if url.endswith(".torrent") or "/download/" in url:
            base_headers["Accept"] = "application/x-bittorrent, application/octet-stream, */*"
        else:
            base_headers["Accept"] = "application/xml, text/xml, */*"
        return base_headers

    async def get_url(self, url, retry=3):
        try_time = 0
        headers = self._get_headers(url)
        while True:
            try:
                req = await self._client.get(url=url, headers=headers)
                logger.debug(f"[Network] Successfully connected to {url}. Status: {req.status_code}")
                req.raise_for_status()
                return req
            except httpx.HTTPStatusError as e:
                logger.warning(f"[Network] HTTP {e.response.status_code} from {url}")
                break
            except httpx.RequestError as e:
                logger.warning(
                    f"[Network] Request error for {url}: {type(e).__name__}. Retry {try_time + 1}/{retry}"
                )
                try_time += 1
                if try_time >= retry:
                    break
                await asyncio.sleep(5)
            except Exception as e:
                logger.warning(f"[Network] Unexpected error for {url}: {e}")
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
        self._client = await get_shared_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Client is shared; do not close it here
        self._client = None
