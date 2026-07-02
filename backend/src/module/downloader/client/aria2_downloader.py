import asyncio
import logging
from typing import ClassVar

import httpx

from module.downloader.base import DownloaderCapabilities

logger = logging.getLogger(__name__)


class Aria2Downloader:
    # Aria2 only speaks "add a download": it has no torrent query, rename,
    # management, or qB-native RSS surface. The facade consults this and skips
    # everything else instead of calling methods that do not exist here.
    capabilities: ClassVar[DownloaderCapabilities] = DownloaderCapabilities(
        can_query=False,
        can_rename=False,
        can_manage=False,
        can_rss_rules=False,
    )

    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.secret = password
        self._client: httpx.AsyncClient | None = None
        self._authed = False
        self._rpc_url = f"{host}/jsonrpc"
        self._id = 0

    async def _call(self, method: str, params: list | None = None):
        assert self._client is not None, "Aria2Downloader.auth() must run first"
        self._id += 1
        if params is None:
            params = []
        # Prepend token
        full_params = [f"token:{self.secret}"] + params
        payload = {
            "jsonrpc": "2.0",
            "id": self._id,
            "method": f"aria2.{method}",
            "params": full_params,
        }
        resp = await self._client.post(self._rpc_url, json=payload)
        result = resp.json()
        if "error" in result:
            raise Exception(f"Aria2 RPC error: {result['error']}")
        return result.get("result")

    async def auth(self, retry=3):
        if self._client is not None and self._authed:
            return True
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=3.1, read=10.0, write=10.0, pool=10.0)
            )
        times = 0
        while times < retry:
            try:
                await self._call("getVersion")
                self._authed = True
                return True
            except Exception as e:
                logger.warning(
                    f"Can't login Aria2 Server {self.host}, retry in 5 seconds. Error: {e}"
                )
                await asyncio.sleep(5)
                times += 1
        return False

    async def logout(self):
        self._authed = False
        if self._client:
            await self._client.aclose()
            self._client = None

    async def torrents_files(self, torrent_hash: str):
        return []

    async def add_torrents(
        self, torrent_urls, torrent_files, save_path, category, tags=None
    ):
        import base64

        options = {"dir": save_path}
        if torrent_urls:
            urls = torrent_urls if isinstance(torrent_urls, list) else [torrent_urls]
            for url in urls:
                await self._call("addUri", [[url], options])
        if torrent_files:
            files = (
                torrent_files if isinstance(torrent_files, list) else [torrent_files]
            )
            for f in files:
                b64 = base64.b64encode(f).decode()
                await self._call("addTorrent", [b64, [], options])
        return True
