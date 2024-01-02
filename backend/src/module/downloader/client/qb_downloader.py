import asyncio
import logging

import httpx
from pydantic import main

from ..exceptions import AuthorizationError, ConflictError

logger = logging.getLogger(__name__)

QB_API_URL = {
    "login": "/api/v2/auth/login",
    "logout": "/api/v2/auth/logout",
    "version": "/api/v2/app/version",
    "setPreferences": "/api/v2/app/setPreferences",
    "createCategory": "/api/v2/torrents/createCategory",
    "info": "/api/v2/torrents/info",
    "add": "/api/v2/torrents/add",
    "delete": "/api/v2/torrents/delete",
    "renameFile": "/api/v2/torrents/renameFile",
    "getFiles": "/api/v2/torrents/files",
    "setLocation": "/api/v2/torrents/setLocation",
    "setCategory": "/api/v2/torrents/setCategory",
    "addTags": "/api/v2/torrents/addTags",
}


class QbDownloader:
    def __init__(self, host: str, username: str, password: str, ssl: bool):
        self.host = host if "://" in host else "http://" + host
        self.username = username
        self.password = password
        self.ssl = ssl

    async def auth(self):
        resp = await self._client.post(
            url=QB_API_URL["login"],
            data={"username": self.username, "password": self.password},
            timeout=5,
        )
        return resp.text == "Ok."

    async def logout(self):
        resp = await self._client.post(
            url=QB_API_URL["logout"],
            timeout=5,
        )
        return resp.text

    async def check_host(self):
        try:
            await self._client.get(
                url=QB_API_URL["version"],
                timeout=5,
            )
            return True
        except httpx.RequestError or httpx.TimeoutException:
            return False

    async def prefs_init(self, prefs):
        await self._client.post(
            url=QB_API_URL["setPreferences"],
            data=prefs,
        )

    async def add_category(self, category: str):
        await self._client.post(
            url=QB_API_URL["createCategory"],
            data={"category": category},
            timeout=5,
        )

    async def torrents_info(self, status_filter, category, tag=None) -> list[dict]:
        """Get torrents info from qbittorrent.
        :param status_filter: Filter torrents by status. Allowed values: all, stalled_downloading
        completed, paused, active, inactive, resumed, stalled, stalled_uploading, stalled_downloading.
        """
        data = {
            "filter": status_filter,
            "category": category,
            "tag": tag,
        }
        torrent_info = await self._client.get(
            url=QB_API_URL["info"],
            params=data,
        )
        return torrent_info.json()

    async def torrent_files(self, _hash) -> dict:
        data = {"hash": _hash}
        torrent_files = await self._client.get(
            url=QB_API_URL["getFiles"],
            params=data,
        )
        return torrent_files.json()

    async def add(self, torrent_urls, torrent_files, save_path, category):
        data = {
            "urls": torrent_urls,
            "torrent_files": torrent_files,
            "save_path": save_path,
            "category": category,
            "is_paused": False,
            "use_auto_torrent_management": False,
        }
        resp = await self._client.post(
            url=QB_API_URL["add"],
            data=data,
        )
        return resp.status_code == 200

    async def delete(self, _hash):
        data = {
            "hashes": _hash,
            "deleteFiles": True,
        }
        resp = await self._client.post(
            url=QB_API_URL["delete"],
            data=data,
        )
        return resp.status_code == 200

    async def rename(self, torrent_hash, old_path, new_path) -> bool:
        data = {
            "hash": torrent_hash,
            "oldPath": old_path,
            "newPath": new_path,
        }
        resp = await self._client.post(
            url=QB_API_URL["renameFile"],
            data=data,
        )
        return resp.status_code == 200

    async def move(self, hashes, new_location):
        data = {
            "hashes": hashes,
            "location": new_location,
        }
        resp = await self._client.post(
            url=QB_API_URL["setLocation"],
            data=data,
        )
        return resp.status_code == 200

    async def set_category(self, _hash, category):
        data = {
            "category": category,
            "hashes": _hash,
        }
        resp = await self._client.post(
            url=QB_API_URL["setCategory"],
            data=data,
        )
        return resp.status_code == 200

    async def add_tag(self, _hash, tag):
        data = {
            "hashes": _hash,
            "tags": tag,
        }
        resp = await self._client.post(
            url=QB_API_URL["addTags"],
            data=data,
        )
        return resp.status_code == 200

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.host,
            trust_env=self.ssl,
        )
        while not await self.check_host():
            logger.warning(
                f"[Downloader] Failed to connect to {self.host}, retry in 30 seconds."
            )
            await asyncio.sleep(30)
        if not await self.auth():
            await self._client.aclose()
            logger.error(
                f"[Downloader] Downloader authorize error. Please check your username/password."
            )
            raise AuthorizationError("Failed to login to qbittorrent.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.logout()
        await self._client.aclose()
