import logging

import httpx
from typing_extensions import override

from models import TorrentDownloadInfo
from models.config import Downloader as DownloaderConfigModel
from module.utils import get_hash

from module.exceptions import ForbiddenError, InvalidCredentialsError, LoginRequiredError

from .base_downloader import BaseDownloader

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
        super().__init__()
        self.api_interval: float = 0.2

    @override
    def initialize(self, config: DownloaderConfigModel) -> None:
        """初始化下载器"""
        # 加载配置
        self.config: DownloaderConfigModel = config
        self._client: httpx.AsyncClient = httpx.AsyncClient(base_url=self.config.host, verify=self.config.ssl)

    @override
    async def auth(self) -> bool:
        """
        几种情况
        1. 200 Ok. 登录成功
        2. 200 Fails. 登录失败，用户名或密码错误,返回 InvalidCredentialsError
        3. 403 Forbidden. IP被封禁，返回 AuthorizationError
        4. 其他网络错误，抛出 httpx.RequestError 异常
        """
        try:
            resp = await self._client.post(
                url=QB_API_URL["login"],
                data={
                    "username": self.config.username,
                    "password": self.config.password,
                },
                timeout=5,
            )
            resp.raise_for_status()
            if resp.status_code == 200 and resp.text == "Ok.":
                logger.debug("[qbittorrent] login success")
                return True
            if resp.status_code == 200 and resp.text == "Fails.":
                logger.error(
                    f"[qbittorrent] login failed, please check your username/password {self.config.username}/{self.config.password}"
                )
                raise InvalidCredentialsError(f"qBittorrent login failed: invalid username or password")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.error(
                    "[qbittorrent] your ip has been banned by qbittorrent, please remove the ban(or restart qbittorrent) and try again."
                )
                raise ForbiddenError(host="qbittorrent")
            logger.error(f"[qbittorrent] HTTP error: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"[qbittorrent] connect to qbittorrent error, please check your host {self.config.host}")
            raise
        return False

    @override
    async def logout(self):
        try:
            resp = await self._client.post(url=QB_API_URL["logout"], timeout=5)
            resp.raise_for_status()
            await self._client.aclose()
            return True
        except httpx.ConnectError or httpx.TimeoutException as e:
            logger.error(f"[qbittorrent] Logout error: {e}")
        except Exception as e:
            logger.error(f"[qbittorrent] final Logout error: {e}")
        return False

    @override
    async def check_host(self) -> bool:
        try:
            logger.debug(f"[qbittorrent] Check host: {self.config.host}")
            resp = await self._client.get(url=QB_API_URL["version"], timeout=5)
            if resp.status_code == 200 or resp.status_code == 403:
                logger.debug(f"[qbittorrent] Check host success: {self.config.host}")
                # 检查
                return True
            resp.raise_for_status()
        except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.TimeoutException, httpx.ReadTimeout) as e:
            logger.error(f"[qbittorrent] Check host error,please check your host {self.config.host}")
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
    async def get_torrent_files(self, hash: str) -> list[str]:
        try:
            data = {"hash": hash}
            reps = await self._client.get(
                url=QB_API_URL["getFiles"],
                params=data,
            )
            reps.raise_for_status()
            if "Not Found" in reps.text:
                logger.warning(f"[qbittorrent] Cannot found {hash}")
                return []
            else:
                files_name = [file["name"] for file in reps.json()]
                return files_name
        except Exception as e:
            self.handle_exception(e, "add_category")

    @override
    async def torrent_info(self, hash: str) -> TorrentDownloadInfo | None:
        try:
            data = {"hash": hash}
            reps = await self._client.get(
                url=QB_API_URL["properties"],
                params=data,
            )
            reps.raise_for_status()
            logger.debug(f"[qbittorrent] Torrent info: {hash}")
            reps = reps.json()
            logger.debug(
                f"[qbittorrent] Torrent info: {reps['eta']=}, {reps['save_path']=}, {reps['completion_date']=}"
            )
            if reps["completion_date"] == -1:
                reps["completion_date"] = 0
            res = TorrentDownloadInfo(
                eta=reps["eta"],
                save_path=reps["save_path"],
                completed=reps["completion_date"],
            )
            return res
        except Exception as e:
            self.handle_exception(e, "torrent_info")

    @override
    async def torrents_info(
        self,
        status_filter: str = "completed",
        category: str = "Bangumi",
        tag: str | None = None,
        limit: int = 0,
    ):
        data: dict[str, str | bool | int | None] = {
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

    @override
    async def add(self, hashs:list[str], torrent_content: bytes|None, save_path: str) -> list[str]:
        """
        会收到 downloader 的标识,qbittorretn 是 hash, alist 是一个标识
        """
        data = {
            "urls": hashs[0],
            "savepath": save_path,
            "category": "AutoBangumi",
            "paused": False,
            "autoTMM": False,
        }
        file = None
        if torrent_content:
            file = {"torrents": torrent_content}
            data.pop("urls", None)  # 移除urls字段
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
                return []
            # 只取前40个字符作为hash
            res = []
            for torrent_link in hashs:
                hash = get_hash(torrent_link)
                # 对 hash v2 做兼容
                if hash:
                    hash = hash[:40]
                    res.append(get_hash(hash))
            return res
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
                    logger.error(f"[qbittorrent] rename error, the file already exists: {old_path} -> {new_path}")
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

    def handle_exception(self, e, funtion_name):
        if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 403:
            logger.error(f"[qbittorrent] {funtion_name} need login first")
            raise LoginRequiredError(endpoint=funtion_name)
        logger.error(f"[qbittorrent] {funtion_name} error: {e}")
        raise
