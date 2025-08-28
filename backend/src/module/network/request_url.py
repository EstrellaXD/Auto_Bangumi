import asyncio
import logging

import httpx

from .proxy import set_proxy

logger = logging.getLogger(__name__)


class RequestURL:
    def __init__(self):
        self.header: dict[str, str] = {
            "user-agent": "Mozilla/5.0",
            "Accept": "application/xml",
        }
        self.proxy: str | None = set_proxy()
        self.retry: int = 3
        self.timeout: int = 5
        self.client: httpx.AsyncClient

    async def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        for attempt in range(self.retry):
            try:
                response = await self.client.request(method, url, follow_redirects=True, **kwargs)
                response.raise_for_status()
                return response
            except httpx.RequestError as e:
                logger.debug(f"[Network] Cannot connect to {url}. Wait for 5 seconds.")
                if attempt < self.retry - 1:
                    await asyncio.sleep(5)
                else:
                    raise e
        # 这里永远不应该执行到，但为了类型安全添加
        raise httpx.RequestError(f"Failed to complete request to {url} after {self.retry} attempts")

    async def get_url(self, url, retry=3):
        self.retry = retry
        return await self._request_with_retry("GET", url)

    async def post_url(
        self,
        url: str,
        data: dict[str, str] | None = None,
        files: dict[str, bytes] | None = None,
        retry: int = 3,
    ) -> httpx.Response:
        self.retry = retry
        resp = await self._request_with_retry("POST", url, data=data, files=files)
        resp.raise_for_status()
        return resp

    async def check_url(self, url: str):
        if not url.startswith("http"):
            url = f"http://{url}"
        try:
            req = await self.client.get(url=url)
            req.raise_for_status()
            return True
        except httpx.RequestError:
            logger.debug(f"[Network] Cannot connect to {url}.")
            return False

    async def __aenter__(self):
        self.client = httpx.AsyncClient(http2=True, proxy=self.proxy, headers=self.header, timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
