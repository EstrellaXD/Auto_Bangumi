import logging
import os

import httpx
from typing_extensions import override

from conf import get_plugin_config
from models import TorrentDownloadInfo
from module.utils import get_hash

from ....conf import settings
from ..base_downloader import BaseDownloader
from ..expection import AuthorizationError
from .config import Config as DownloaderConfig

logger = logging.getLogger(__name__)


ALIST_API_URL = {
    "auth": "/api/auth/login",
    "ping": "/api/ping",
    "list": "/api/fs/list",
    "get": "/api/fs/get",
    "mkdir": "/api/fs/mkdir",
    "rename": "/api/fs/rename",
    "move": "/api/fs/move",
    "copy": "/api/fs/copy",
    "remove": "/api/fs/remove",
    "put": "/api/fs/put",
    "add_offline": "/api/fs/add_offline_download",
    "offline_list": "/api/task/offline_download/list",
    "offline_list_done": "/api/task/offline_download/done",
    "offline_info": "/api/task/offline_download/info",
    "offline_delete": "/api/task/offline_download/delete",
}


class Downloader(BaseDownloader):
    def __init__(self):
        super().__init__()
        self._client: httpx.AsyncClient | None = None
        self.config: DownloaderConfig = get_plugin_config(DownloaderConfig(), "downloader")
        self.api_interval: float = 1.0

    @override
    def initialize(self) -> None:
        """初始化下载器"""
        # 加载配置
        self.config = get_plugin_config(DownloaderConfig(), "downloader")
        self.headers: dict[str, str] = {
            "Authorization": f"{self.config.password}",
        }
        self._client = httpx.AsyncClient(base_url=self.config.host, verify=settings.downloader.ssl)

    @override
    async def auth(self) -> bool:
        return True

    @override
    async def logout(self) -> bool:
        return True

    @override
    async def check_host(self) -> bool:
        try:
            resp = await self._client.get(
                url=ALIST_API_URL["ping"],
                timeout=5,
            )
            resp.raise_for_status()
            if resp.status_code == 200:
                logger.debug(f"[openlist] Successfully connected to {self.config.host}")
                return True
        except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadTimeout) as e:
            logger.error(f"[openlist] Check host error, please check your host {self.config.host}")
            logger.debug(f"[openlist] Check host error: {e}")

        return False

    async def torrent_info(self, hash: str) -> TorrentDownloadInfo:
        # TODO:
        #
        res = TorrentDownloadInfo(eta=0, save_path=settings.downloader.path, completed=1)
        return res
        """
                    {'id': 'CImUQ9ZzMsBc5JB3G4EyH',
                 'name': 'download magnet:?xt=urn:btih:96733a847f1de1c01f524ad6983a4f8b39ee5bfb&tr=http%3a%2f%2ft.nyaatracker.com%2fannounce&t
        r=http%3a%2f%2ftracker.kamigami.org%3a2710%2fannounce&tr=http%3a%2f%2fshare.camoe.cn%3a8080%2fannounce&tr=http%3a%2f%2fopentracker.acgnx.se%2fannounce&tr=htt
        p%3a%2f%2fanidex.moe%3a6969%2fannounce&tr=http%3a%2f%2ft.acg.rip%3a6699%2fannounce&tr=https%3a%2f%2ftr.bangumi.moe%3a9696%2fannounce&tr=udp%3a%2f%2ftr.bangum
        i.moe%3a6969%2fannounce&tr=http%3a%2f%2fopen.acgtracker.com%3a1096%2fannounce&tr=udp%3a%2f%2ftracker.opentrackr.org%3a1337%2fannounce to (/115/游戏)',
                 'creat or': 'shino',
                 'creator_role': 2,
                 'state': 2,
                 'status': '[115 Cloud]: 离线下载完成',
                 'progress': 100,
                 'start_time': '2025-06-27T01:48:31.5065372Z',
                 'end_time' : '2025-06-27T01:48:48.514764101Z',
                 'total_bytes': 238636042,
                 'error': ''}
        """
        parmas = {"tid": hash}
        try:
            resp = await self._client.post(
                url=ALIST_API_URL["offline_info"],
                params=parmas,
            )
            resp.raise_for_status()
            result = resp.json()
            print(result)
            if result.get("code") == 200:
                tasks = result.get("data", {})
                print(tasks)
            return []
        except Exception as e:
            self.handle_exception(e, "get_torrent_files")
            return []

    @override
    async def get_torrent_files(self, hash: str) -> list[str] | None:
        # TODO:
        return []

    @override
    async def torrents_info(
        self,
        status_filter: str = "completed",
        category: str = "Bangumi",
        tag: str | None = None,
        limit: int = 0,
    ):
        return []

    @override
    async def add(self, torrent_url: str, save_path, category) -> str | bool:
        try:
            save_path = settings.downloader.path
            if not torrent_url:
                return False

            torrent_hash = get_hash(torrent_url)
            torrent_url = f"magnet:?xt=urn:btih:{torrent_hash}"
            data = {
                "urls": [torrent_url],
                "path": save_path,
                "tool": "115 Cloud",
            }

            resp = await self._client.post(
                url=ALIST_API_URL["add_offline"],
                json=data,
            )
            resp.raise_for_status()
            result = resp.json()
            #         {
            #     "code": 200,
            #     "message": "success",
            #     "data": {
            #         "tasks": [
            #             {
            #                 "id": "KYIDxrZZJ9fiympt2m-CE",
            #                 "name": "download magnet:?xt=urn:btih:9060b224735b3d152772f253c6b22b9f20fa158b\u0026tr=http%3a%2f%2ft.nyaatracker.com%2fannounce\u0026tr=http%3a%2f%2ftracker.kamigami.org%3a2710%2fannounce\u0026tr=http%3a%2f%2fshare.camoe.cn%3a8080%2fannounce\u0026tr=http%3a%2f%2fopentracker.acgnx.se%2fannounce\u0026tr=http%3a%2f%2fanidex.moe%3a6969%2fannounce\u0026tr=http%3a%2f%2ft.acg.rip%3a6699%2fannounce\u0026tr=https%3a%2f%2ftr.bangumi.moe%3a9696%2fannounce\u0026tr=udp%3a%2f%2ftr.bangumi.moe%3a6969%2fannounce\u0026tr=http%3a%2f%2fopen.acgtracker.com%3a1096%2fannounce\u0026tr=udp%3a%2f%2ftracker.opentrackr.org%3a1337%2fannounce to (/115/视频/缓冲)",
            #                 "creator": "shino",
            #                 "creator_role": 2,
            #                 "state": 0,
            #                 "status": "",
            #                 "progress": 0,
            #                 "start_time": null,
            #                 "end_time": null,
            #                 "total_bytes": 0,
            #                 "error": ""
            #             }
            #         ]
            #     }
            # }
            logger.debug(f"[openlist] add torrent result: {result['data']['tasks']}")

            if result.get("code") != 200:
                logger.error(f"[openlist] add torrent failed: {result.get('message', 'Unknown error')}")
                return False

            logger.debug(f"[openlist] Successfully added torrent: {torrent_url}")
            return result["data"]["tasks"][0]["id"] if result["data"]["tasks"] else False
        except Exception as e:
            self.handle_exception(e, "add")
            return False

    @override
    async def delete(self, hashes: list[str] | str) -> bool:
        # TODO:
        return True
        try:
            if isinstance(hashes, str):
                hashes = [hashes]

            for hash_id in hashes:
                resp = await self._client.post(
                    url=ALIST_API_URL["offline_delete"],
                    json={"tid": hash_id},
                )
                resp.raise_for_status()
                result = resp.json()

                if result.get("code") != 200:
                    logger.error(
                        f"[openlist] delete torrent {hash_id} failed: {result.get('message', 'Unknown error')}"
                    )
                    return False

            return True
        except Exception as e:
            self.handle_exception(e, "delete")
            return False

    @override
    async def rename(self, torrent_hash: str, old_path: str, new_path: str) -> bool:
        # TODO:
        return True
        try:
            data = {
                "path": old_path,
                "name": os.path.basename(new_path),
            }
            resp = await self._client.post(
                url=ALIST_API_URL["rename"],
                json=data,
            )
            resp.raise_for_status()
            result = resp.json()

            if result.get("code") == 200:
                logger.debug(f"[openlist] Successfully renamed {old_path} to {new_path}")
                return True
            else:
                logger.error(f"[openlist] rename failed: {result.get('message', 'Unknown error')}")
                return False
        except Exception as e:
            self.handle_exception(e, "rename")
            return False

    @override
    async def move(self, hashes, new_location) -> bool:
        # TODO:
        return True
        try:
            if isinstance(hashes, list):
                hashes = "|".join(hashes)

            torrent_infos = await self.torrents_info(status_filter="all", limit=0)

            for torrent_info in torrent_infos:
                if torrent_info["hash"] in hashes:
                    old_path = torrent_info["save_path"]

                    data = {
                        "dir": os.path.dirname(old_path),
                        "dst_dir": new_location,
                        "names": [os.path.basename(old_path)],
                    }

                    resp = await self._client.post(
                        url=ALIST_API_URL["move"],
                        json=data,
                    )
                    resp.raise_for_status()
                    result = resp.json()

                    if result.get("code") != 200:
                        logger.error(
                            f"[openlist] move {old_path} to {new_location} failed: {result.get('message', 'Unknown error')}"
                        )
                        return False

            return True
        except Exception as e:
            self.handle_exception(e, "move")
            return False

    async def create_folder(self, path: str) -> bool:
        # TODO:
        return True
        try:
            data = {"path": path}
            resp = await self._client.post(
                url=ALIST_API_URL["mkdir"],
                json=data,
            )
            resp.raise_for_status()
            result = resp.json()

            if result.get("code") == 200:
                logger.debug(f"[openlist] Successfully created folder {path}")
                return True
            else:
                logger.error(f"[openlist] create folder failed: {result.get('message', 'Unknown error')}")
                return False
        except Exception as e:
            self.handle_exception(e, "create_folder")
            return False

    def handle_exception(self, e, function_name):
        if isinstance(e, httpx.HTTPStatusError):
            if e.response.status_code == 401:
                logger.error(f"[openlist] {function_name} need authentication")
                raise AuthorizationError(function_name)
            elif e.response.status_code == 403:
                logger.error(f"[openlist] {function_name} forbidden")
                raise AuthorizationError(function_name)
            else:
                logger.error(f"[openlist] {function_name} error: {e}")
        else:
            logger.error(f"[openlist] {function_name} error: {e}")
