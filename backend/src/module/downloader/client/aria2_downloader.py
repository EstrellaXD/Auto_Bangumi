import asyncio
import logging

import httpx

from module.conf import settings

logger = logging.getLogger(__name__)


class Aria2Downloader:
    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.secret = password
        self._client: httpx.AsyncClient | None = None
        self._rpc_url = f"{host}/jsonrpc"
        self._id = 0

    async def _call(self, method: str, params: list = None):
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
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(connect=3.1, read=10.0, write=10.0, pool=10.0))
        times = 0
        while times < retry:
            try:
                await self._call("getVersion")
                return True
            except Exception as e:
                logger.warning(
                    f"Can't login Aria2 Server {self.host}, retry in 5 seconds. Error: {e}"
                )
                await asyncio.sleep(5)
                times += 1
        return False

    async def logout(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def add_torrents(self, torrent_urls, torrent_files, save_path, category):
        import base64
        options = {"dir": save_path}
        if torrent_urls:
            urls = torrent_urls if isinstance(torrent_urls, list) else [torrent_urls]
            for url in urls:
                await self._call("addUri", [[url], options])
        if torrent_files:
            files = torrent_files if isinstance(torrent_files, list) else [torrent_files]
            for f in files:
                b64 = base64.b64encode(f).decode()
                await self._call("addTorrent", [b64, [], options])
        return True
