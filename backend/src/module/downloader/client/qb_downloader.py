import asyncio
import logging

import httpx

from ..exceptions import AuthorizationError

logger = logging.getLogger(__name__)

QB_API_URL = {
    "add": "/api/v2/torrents/add",
    "addTags": "/api/v2/torrents/addTags",
    "createCategory": "/api/v2/torrents/createCategory",
    "delete": "/api/v2/torrents/delete",
    "getFiles": "/api/v2/torrents/files",
    "info": "/api/v2/torrents/info",
    "login": "/api/v2/auth/login",
    "logout": "/api/v2/auth/logout",
    "renameFile": "/api/v2/torrents/renameFile",
    "setCategory": "/api/v2/torrents/setCategory",
    "setLocation": "/api/v2/torrents/setLocation",
    "setPreferences": "/api/v2/app/setPreferences",
    "version": "/api/v2/app/version",
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
        resp = await self._client.post(url=QB_API_URL["logout"], timeout=5)
        return resp.text

    async def check_host(self):
        try:
            await self._client.get(url=QB_API_URL["version"], timeout=5)
            return True
        except httpx.ConnectError or httpx.TimeoutException as e:
            return False

    async def prefs_init(self, prefs):
        await self._client.post(url=QB_API_URL["setPreferences"], data=prefs)

    async def add_category(self, category):
        await self._client.post(
            url=QB_API_URL["createCategory"],
            data={"category": category},
            timeout=5,
        )

    async def get_torrent_files(self, _hash: str) -> list[str]:
        data = {"hash": _hash}
        reps = await self._client.get(
            url=QB_API_URL["getFiles"],
            params=data,
        )
        if "Not Found" in reps.text:
            logging.warning(f"Cannot found {_hash}")
            return []
        files_name = [file["name"] for file in reps.json()]
        return files_name

    async def torrents_info(self, status_filter, category, tag=None, limit=0):
        data = {
            "filter": status_filter,
            "category": category,
            "tag": tag,
        }
        if limit:
            data.update({"limit": limit})
        torrent_infos = await self._client.get(
            url=QB_API_URL["info"],
            params=data,
        )
        torrent_infos_list = []
        for torrent_info in torrent_infos.json():
            torrent_infos_list.append(
                {
                    "hash": torrent_info["hash"],
                    "save_path": torrent_info["save_path"],
                    "name": torrent_info["name"]
                }
            )
        return torrent_infos.json()

    async def add(self, torrent_urls, torrent_files, save_path, category):
        data = {
            "urls": torrent_urls,
            "savepath": save_path,
            "category": category,
            "paused": False,
            "autoTMM": False,
        }

        file = None
        if torrent_files:
            file = {"torrents": torrent_files}

        resp = await self._client.post(
            url=QB_API_URL["add"],
            data=data,
            files=file,
        )
        if "fail"in resp.text.lower() :
            logger.debug(f"[QbDownloader] A BAD TORRENT{save_path} , send torrent to download fail.{resp.text.lower()}")
            return False
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
        """
        并不返回任何东西,所以不知道结果
        """
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
        """
        hashes: "hash1|hash2|..."
        """

        if isinstance(hashes,list):
            hashes = "|".join(hashes)
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
                "[Downloader] Downloader authorize error. Please check your username/password."
            )
            raise AuthorizationError("Failed to login to qbittorrent.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.logout()
        await self._client.aclose()
