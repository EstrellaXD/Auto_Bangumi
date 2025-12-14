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
        self.timeout: int = 5
        self.client: httpx.AsyncClient

    async def _request_with_retry(self, method: str, url: str, retry: int = 3, **kwargs) -> httpx.Response:
        last_exception: Exception | None = None
        for attempt in range(retry):
            try:
                response = await self.client.request(method, url, follow_redirects=True, **kwargs)
                response.raise_for_status()
                return response
            except httpx.RequestError as e:
                if isinstance(e, httpx.HTTPStatusError) and 400 <= e.response.status_code < 500:
                    logger.debug(f"[Network] HTTP error {e.response.status_code} for {url}. Not retrying.")
                    raise
                logger.debug(f"[Network] Cannot connect to {url}. Wait for 5 seconds.")
                last_exception = e

            if attempt < retry - 1:
                logger.debug(f"[Network] Retry {attempt + 1} for {url}.")
                await asyncio.sleep(5)
        if last_exception:
            raise last_exception

        raise httpx.RequestError(f"Failed after {retry} attempts")

    async def get_url(self, url, retry: int = 3) -> httpx.Response:
        return await self._request_with_retry("GET", url, retry=retry)

    async def post_url(
        self,
        url: str,
        data: dict[str, str] | None = None,
        files: dict[str, bytes] | None = None,
        retry: int = 3,
    ) -> httpx.Response:
        return await self._request_with_retry("POST", url, retry=retry, data=data, files=files)

    async def __aenter__(self):
        self.client = httpx.AsyncClient(http2=True, proxy=self.proxy, headers=self.header, timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
