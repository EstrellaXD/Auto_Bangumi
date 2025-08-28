import asyncio
import base64
import logging

import httpx

from ..exceptions import AuthorizationError

logger = logging.getLogger(__name__)


class TrDownloader:
    def __init__(self, host, username, password, ssl):
        self.host = host if "://" in host else "http://" + host
        self.username = username
        self.password = password
        self.ssl = ssl
        self.authkey = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()

        self._client = httpx.AsyncClient(
            base_url=self.host,
            auth=(self.username, self.password),
            timeout=5,
        )

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.host,
        )

        while not await self.check_host():
            logger.warning(f"[Downloader] Failed to connect to {self.host}, retry in 30 seconds.")
            await asyncio.sleep(30)
        if not await self.auth():
            await self._client.aclose()
            raise AuthorizationError("Failed to login to transmission.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.logout()
        await self._client.aclose()

    async def auth(self):
        # NOTE: Transmission will return 409 when first login
        if self.username and self.password:
            self._client.headers.update({"Authorization": f"Basic {self.authkey}"})

        resp = await self._client.post("/transmission/rpc")

        if resp.status_code == 409 and "X-Transmission-Session-Id" in resp.headers:
            self._client.headers.update({"X-Transmission-Session-Id": resp.headers["X-Transmission-Session-Id"]})
            resp = await self._client.post("/transmission/rpc")
        elif resp.status_code == 401:
            logger.error("Transmission: Authentication failed")
            return False

        return resp.status_code == 200

    def logout(self):
        self._client.headers.pop("Authorization")

    async def check_host(self):
        try:
            await self._client.get("/transmission/web/")
            return True
        except httpx.RequestError:
            return False

    async def add_torrent(self, download_link=None, torrent_path=None, save_path=None, **kwargs):
        if not download_link and not torrent_path:
            # WARNING: Regard no torrent as success
            return True
        request_data = {
            "method": "torrent-add",
            "arguments": {"download-dir": save_path, "paused": False, **kwargs},
        }

        if torrent_path:
            try:
                with open(torrent_path, "rb") as file:
                    file_content = file.read()
                metainfo = base64.b64encode(file_content).decode()
            except FileNotFoundError:
                logger.error(f"File not found: {torrent_path}")
                return False

            request_data["arguments"].update({"metainfo": metainfo})
        else:
            request_data["arguments"].update({"filename": download_link})

        resp = await self._client.post("/transmission/rpc", json=request_data)

        return resp.status_code == 200

    async def add(self, torrent_urls, torrent_files, save_path, category):
        result = True
        for torrent_url in torrent_urls:
            result = result and await self.add_torrent(
                download_link=torrent_url, save_path=save_path, labels=[category]
            )

        for torrent_file in torrent_files:
            result = result and await self.add_torrent(torrent_path=torrent_file, save_path=save_path)

        return result

    async def delete(self, _hash):
        request_data = {
            "method": "torrent-remove",
            "arguments": {"ids": [_hash], "delete-local-data": True},
        }
        resp = await self._client.post("/transmission/rpc", json=request_data)
        return resp.status_code == 200

    async def move(self, hashes, new_location):
        request_data = {
            "method": "torrent-set-location",
            "arguments": {"ids": hashes, "location": new_location},
        }
        resp = await self._client.post("/transmission/rpc", json=request_data)
        return resp.status_code == 200

    async def rename(self, torrent_hash, old_path, new_path) -> bool:
        request_data = {
            "method": "torrent-rename-path",
            "arguments": {"ids": [torrent_hash], "path": old_path, "name": new_path},
        }
        resp = await self._client.post("/transmission/rpc", json=request_data)
        return resp.status_code == 200

    async def torrents_info(self, status_filter, category, tag=None):
        KEY_MAP = {"hashString": "hash", "downloadDir": "save_path"}
        # Map transmission key to qbittorrent

        request_data = {
            "method": "torrent-get",
            "arguments": {
                "fields": [
                    "id",
                    "name",
                    "hashString",
                    "downloadDir",
                    "status",
                    "labels",
                ],
            },
            "format": "object",
        }
        resp = await self._client.post("/transmission/rpc", json=request_data)
        data = resp.json()
        torrents_info = data["arguments"].get("torrents")
        for torrent_info in torrents_info:
            for old_key, new_key in KEY_MAP.items():
                torrent_info[new_key] = torrent_info.pop(old_key)

        torrents_info = self._filter_status(torrents_info, status_filter)
        if category:
            torrents_info = [torrent for torrent in torrents_info if category in torrent["labels"]]
        # NOTE: To compatible with qbittorrent api we use category as label

        return torrents_info

    async def set_category(self, torrent_hashes, category):
        request_data = {
            "method": "torrent-set",
            "arguments": {"ids": torrent_hashes, "labels": [category]},
        }

        # NOTE: To compatible with qbittorrent api we use category as label
        resp = await self._client.post("/transmission/rpc", json=request_data)
        return resp.status_code == 200

    def _filter_status(self, torrents_info, status_filter: str):
        """
        Filter torrents by status
        Docs: https://github.com/transmission/transmission/blob/main/docs/rpc-spec.md#33-torrent-accessor-torrent-get
        """
        if status_filter == "completed":
            # We regard torrents queue to seed as completed
            return [torrent for torrent in torrents_info if torrent["status"] >= 5]
        elif status_filter == "downloading":
            return [torrent for torrent in torrents_info if torrent["status"] == 4]
        elif status_filter == "inactive":
            return [torrent for torrent in torrents_info if torrent["status"] <= 3]

        return torrents_info
