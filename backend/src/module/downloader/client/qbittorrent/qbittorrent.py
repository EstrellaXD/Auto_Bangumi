import logging

import httpx
from typing_extensions import override
from module.models import TorrentDownloadInfo

from module.conf import get_plugin_config

from ....conf import settings
from ..base_downloader import BaseDownloader
from ..expection import AuthorizationError
from .config import Config as DownloaderConfig
from module.network import RequestContent

logger = logging.getLogger(__name__)


QB_API_URL = {
    "add": "/api/v2/torrents/add",
    "addTags": "/api/v2/torrents/addTags",
    "createCategory": "/api/v2/torrents/createCategory",
    "delete": "/api/v2/torrents/delete",
    "getFiles": "/api/v2/torrents/files",
    "info": "/api/v2/torrents/info",
    "properties": "/api/v2/torrents/properties",
    "login": "/api/v2/auth/login",
    "logout": "/api/v2/auth/logout",
    "renameFile": "/api/v2/torrents/renameFile",
    "setCategory": "/api/v2/torrents/setCategory",
    "setLocation": "/api/v2/torrents/setLocation",
    "setPreferences": "/api/v2/app/setPreferences",
    "version": "/api/v2/app/version",
}


class Downloader(BaseDownloader):

    def __init__(self):  # , host: str, username: str, password: str, ssl: bool
        self.config: DownloaderConfig = get_plugin_config(
            DownloaderConfig(), "downloader"
        )
        self.host: str = self.config.host
        self.username: str = self.config.username
        self.password: str = self.config.password
        self.ssl: bool = settings.downloader.ssl
        self._client: httpx.AsyncClient = httpx.AsyncClient(
            base_url=self.host,
            trust_env=self.ssl,
        )

    @override
    async def auth(self):
        try:
            resp = await self._client.post(
                url=QB_API_URL["login"],
                data={"username": self.username, "password": self.password},
                timeout=5,
            )
            resp.raise_for_status()
            if resp.status_code == 200 and resp.text == "Ok.":
                logger.debug("[qbittorrent] login success")
                return True
            if resp.status_code == 200 and resp.text == "Fails.":
                logger.error(
                    f"[qbittorrent] login failed, please check your username/password {self.username}/{self.password}"
                )
                return False
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.error(
                    "[qbittorrent] your ip has been banned by qbittorrent, please remove the ban(or restart qbittorrent) and try again."
                )
        except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadTimeout) as e:
            logger.error(
                f"[qbittorrent] connect to qbittorrent error, please check your host {self.host}"
            )
        return False

    @override
    async def logout(self):
        try:
            resp = await self._client.post(url=QB_API_URL["logout"], timeout=5)
            resp.raise_for_status()
            return True
        except httpx.ConnectError or httpx.TimeoutException as e:
            logger.error(f"[qbittorrent] Logout error: {e}")
        except Exception as e:
            logger.error(f"[qbittorrent] final Logout error: {e}")
        return False

    @override
    async def check_host(self):
        try:
            resp = await self._client.get(url=QB_API_URL["version"], timeout=5)
            resp.raise_for_status()
            if resp.status_code == 200:
                return True
            return False
        except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadTimeout) as e:
            logger.error(
                f"[qbittorrent] Check host error,please check your host {self.host}"
            )
            logger.debug(f"[qbittorrent] Check host error: {e}")
        return False

    async def prefs_init(self, prefs):
        await self._client.post(url=QB_API_URL["setPreferences"], data=prefs)

    async def add_category(self, category) -> bool:
        try:
            await self._client.post(
                url=QB_API_URL["createCategory"],
                data={"category": category},
                timeout=5,
            )
        except Exception as e:
            self.handle_exception(e, "add_category")
        return False

    @override
    async def get_torrent_files(self, hash: str) -> list[str] | None:
        try:
            data = {"hash": hash}
            reps = await self._client.get(
                url=QB_API_URL["getFiles"],
                params=data,
            )
            reps.raise_for_status()
            if "Not Found" in reps.text:
                logger.warning(f"[qbittorrent] Cannot found {hash}")
                return None
            else:
                files_name = [file["name"] for file in reps.json()]
                return files_name
        except Exception as e:
            self.handle_exception(e, "add_category")
        return []

    async def torrent_info(self, hash: str)-> TorrentDownloadInfo | None:
        try:
            data = {"hash": hash}
            reps = await self._client.get(
                url=QB_API_URL["properties"],
                params=data,
            )
            reps.raise_for_status()
            if "404" in reps.text:
                logger.warning(f"[qbittorrent] Cannot found {hash}")
                return None
            else:
                logger.debug(f"[qbittorrent] Torrent info: {hash}")
                reps = reps.json()
                res = TorrentDownloadInfo(eta = reps["eta"], save_path=reps["save_path"],completed=reps["completion_date"])
                return res
        except Exception as e:
            self.handle_exception(e, "torrent_info")
        return None

    @override
    async def torrents_info(
        self,
        status_filter: str = "completed",
        category: str = "Bangumi",
        tag: str | None = None,
        limit: int = 0,
    ):
        data = {
            "filter": status_filter,
            "category": category,
            "tag": tag,
            "sort": "completion_on",
            "reverse": True,
        }
        if limit:
            data.update({"limit": limit})
        try:
            torrent_infos = await self._client.get(
                url=QB_API_URL["info"],
                params=data,
            )
            torrent_infos.raise_for_status()
            torrent_infos_list = []
            for torrent_info in torrent_infos.json():
                torrent_infos_list.append(
                    {
                        "hash": torrent_info["hash"],
                        "save_path": torrent_info["save_path"],
                        "name": torrent_info["name"],
                    }
                )
            return torrent_infos.json()
        except Exception as e:
            self.handle_exception(e, "torrents_info")
            return []

    @override
    async def add(self, torrent_urls, torrent_file, save_path, category) -> str | None:
        """
        会收到 downloader 的标识,qbittorretn 是 hash, alist 是一个标识
        """
        data = {
            "urls": torrent_urls,
            "savepath": save_path,
            "category": category,
            "paused": False,
            "autoTMM": False,
        }
        file = None
        torrent_link = ""
        async with RequestContent() as req:
            if torrent_file := await req.get_content(torrent_urls):
                torrent_link = await req.get_torrent_hash(torrent_urls)
                file = {"torrents": torrent_file}
        try:
            resp = await self._client.post(
                url=QB_API_URL["add"],
                data=data,
                files=file,
            )
            resp.raise_for_status()
            if "fail" in resp.text.lower():
                logger.debug(
                    f"[QbDownloader] A BAD TORRENT{save_path} , send torrent to download fail.{resp.text.lower()}"
                )
            if resp.status_code == 200:
                return torrent_link
        except Exception as e:
            self.handle_exception(e, "add")

    @override
    async def delete(self, hashes: list[str] | str) -> bool:
        """
        并不返回任何东西,所以不知道结果
        """

        if isinstance(hashes, list):
            hashes = "|".join(hashes)
        data = {
            "hashes": hashes,
            "deleteFiles": True,
        }
        try:
            resp = await self._client.post(
                url=QB_API_URL["delete"],
                data=data,
            )
            resp.raise_for_status()
            return resp.status_code == 200
        except Exception as e:
            self.handle_exception(e, "delete")
            return False

    @override
    async def rename(self, torrent_hash: str, old_path: str, new_path: str) -> bool:
        """
        并不返回任何东西,所以不知道结果
        """
        try:
            data = {
                "hash": torrent_hash,
                "oldPath": old_path,
                "newPath": new_path,
            }
            resp = await self._client.post(
                url=QB_API_URL["renameFile"],
                data=data,
            )
            resp.raise_for_status()
            return resp.status_code == 200
        except Exception as e:
            if isinstance(e, httpx.HTTPStatusError):
                if e.response.status_code == 409:
                    logger.error(
                        f"[qbittorrent] rename error, the file already exists: {old_path} -> {new_path}"
                    )
            else:
                self.handle_exception(e, "rename")
            return False

    @override
    async def move(self, hashes, new_location):
        """
        hashes: "hash1|hash2|..."
        """

        if isinstance(hashes, list):
            hashes = "|".join(hashes)
        data = {
            "hashes": hashes,
            "location": new_location,
        }
        try:
            resp = await self._client.post(
                url=QB_API_URL["setLocation"],
                data=data,
            )
            resp.raise_for_status()
            return resp.status_code == 200
        except Exception as e:
            self.handle_exception(e, "move")
            return False

    async def set_category(self, _hash: str, category: str) -> bool:
        data = {
            "category": category,
            "hashes": _hash,
        }
        try:
            resp = await self._client.post(
                url=QB_API_URL["setCategory"],
                data=data,
            )
            resp.raise_for_status()
            return resp.status_code == 200
        except Exception as e:
            self.handle_exception(e, "set_category")
            return False

    async def add_tag(self, _hash, tag) -> bool:
        data = {
            "hashes": _hash,
            "tags": tag,
        }
        try:
            resp = await self._client.post(
                url=QB_API_URL["addTags"],
                data=data,
            )
            resp.raise_for_status()
            return resp.status_code == 200
        except Exception as e:
            self.handle_exception(e, "add_tag")
            return False

    def handle_exception(self, e, funtion_name):
        if isinstance(e, httpx.HTTPStatusError):
            if e.response.status_code == 403:
                logger.error(f"[qbittorrent] {funtion_name} need login first")
                raise AuthorizationError(funtion_name)
            else:
                logger.error(f"[qbittorrent] {funtion_name} error: {e}")
        else:
            logger.error(f"[qbittorrent] {funtion_name} error: {e}")
