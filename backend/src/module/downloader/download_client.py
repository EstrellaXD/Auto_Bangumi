import asyncio
import importlib
import logging
from asyncio import Task
from typing import Any

from module.models import Torrent
from module.network import RequestContent
from module.utils import get_hash, torrent_to_link

from ..conf import settings
from .client import AuthorizationError, BaseDownloader
from .path import TorrentPath

logger = logging.getLogger(__name__)


class DownloadClient:
    """
    下载器客户端
    处理所有下载器相关操作, 对错误进行重试, 不对外暴露错误,看起来是正常运行
    """

    def __init__(self):
        self.downloader: BaseDownloader = self.get_downloader()
        self._path_parser: TorrentPath = TorrentPath()
        self.tasks: list[Task[Any]] = []
        self.is_logining: bool = False
        self.is_running: bool = True
        # 用于等待登陆完成
        self.is_login: bool = False
        self.login_event: asyncio.Event = asyncio.Event()
        self.login_success_event: asyncio.Event = asyncio.Event()
        self.login_timeout = 30  # 登录超时时间(秒)

    async def __aenter__(self):
        if not self.is_login:
            self.login_event.set()
        if not self.is_logining:
            self.start_login()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def login(self):
        # 当没有登陆,并且没有登陆事件时
        try:
            self.is_logining = True
            times = 0
            while True:
                logger.debug("[Downloader Client] login")
                await self.login_event.wait()
                self.login_success_event.clear()
                if await self.downloader.auth():
                    self.login_success_event.set()
                    self.login_event.clear()
                    self.is_login = True
                    logger.info("[Downloader Client] login success")
                else:
                    times += 1
                    # 最大为 5 分钟
                    if times > 10:
                        times = 10
                    logger.info(
                        f"[Downloader Client] login failed, retry after {30*times}s"
                    )
                    await asyncio.sleep(times * 30)
        except Exception as e:
            logger.error(f"[Downloader Client] login error: {e}")
            self.is_logining = False

    async def wait_for_login(self) -> bool:
        """等待登录完成，超时返回False"""
        try:
            await asyncio.wait_for(self.login_success_event.wait(), self.login_timeout)
            return True
        except asyncio.TimeoutError:
            logger.warning("[Downloader Client] Login wait timeout")
            raise AuthorizationError("login")

    async def get_torrent_info(
        self, category="Bangumi", status_filter="completed", tag=None, limit=0
    ):
        try:
            await self.wait_for_login()
            resp = await self.downloader.torrents_info(
                category=category,
                status_filter=status_filter,
                tag=tag,
                limit=limit,
            )
            return resp
        except AuthorizationError:
            self.start_login()
            return []

    async def add_torrent(self, torrent: Torrent, bangumi) -> bool:
        try:
            await self.wait_for_login()
            bangumi.save_path = self._path_parser.gen_save_path(bangumi)
            torrent_file = None
            torrent_url = torrent.url
            # print(f"add torrent {torrent.url}")
            if torrent.url.startswith("magnet"):
                torrent_url = torrent.url
            else:
                async with RequestContent() as req:
                    # 下载种子文件,处理 hash 与 url 不一致的情况
                    if torrent_file := await req.get_content(torrent.url):
                        torrent_url_hash = get_hash(torrent_url)
                        torrent_url = await torrent_to_link(torrent_file)
                        torrent_hash = get_hash(torrent_url)
                        if torrent_hash != torrent_url_hash:
                            torrent.url = f"{torrent.url},{torrent_hash}"
            logging.debug(f"[Downloader] send url {torrent_url}to downloader ")

            result = await self.downloader.add(
                torrent_urls=torrent_url,
                torrent_files=torrent_file,
                save_path=bangumi.save_path,
                category="Bangumi",
            )
            if result:
                logger.debug(f"[Downloader] Add torrent: {torrent.name}")
                return True
            else:
                logger.warning(
                    f"[Downloader] Torrent added failed: {torrent.name},{torrent.url=}"
                )
        except AuthorizationError:
            self.start_login()
        return False

    async def move_torrent(self, hashes: list[str] | str, location: str) -> bool:
        try:
            await self.wait_for_login()
            result = await self.downloader.move(hashes=hashes, new_location=location)
            if result:
                logger.info(f"[Downloader] Move torrents {hashes} to {location}")
                return True
            else:
                logger.warning(
                    f"[Downloader] Move torrents {hashes} to {location} failed"
                )
                return False
        except AuthorizationError:
            self.start_login()
        return False

    # async def set_category(self, hashes, category):
    #     await self.downloader.set_category(hashes, category)

    async def rename_torrent_file(
        self, torrent_hash: str, old_path: str, new_path: str
    ) -> bool:
        try:
            await self.wait_for_login()
            result = await self.downloader.rename(
                torrent_hash=torrent_hash,
                old_path=old_path,
                new_path=new_path,
            )
            if result:
                logger.info(f"[Downloader] rename {old_path} >> {new_path}")
                return True
            else:
                logger.warning(f"[Downloader] rename {old_path} >> {new_path} failed")
                return False
        except AuthorizationError:
            self.start_login()
        return False

    async def delete_torrent(self, hashes: list[str] | str) -> bool:
        try:
            await self.wait_for_login()
            result = await self.downloader.delete(hashes)
            if result:
                logger.debug(f"[Downloader] Remove torrents {hashes}.")
                return True
            else:
                logger.warning(f"[Downloader] Remove torrents {hashes} failed")
                return False
        except AuthorizationError:
            self.start_login()
        return False

    async def get_torrent_files(self, _hash: str) -> list[str]:
        # 获取种子文件列表
        # 文件夹举例
        # LKSUB][Make Heroine ga Oosugiru!][01-12][720P]/[LKSUB][Make Heroine ga Oosugiru!][01][720P].mp4
        try:
            await self.wait_for_login()
            return await self.downloader.get_torrent_files(_hash)
        except AuthorizationError:
            self.start_login()
        return []

    def start_login(self):
        self.is_login = False
        self.login_event.set()
        if not self.is_logining:
            asyncio.create_task(self.login(), name="login")

    def start(self):
        self.downloader = self.get_downloader()
        # 判断有没有 login task
        self.start_login()

    async def stop(self):
        for task in self.tasks:
            task.cancel()
        await self.downloader.logout()

    async def restart(self):
        await self.stop()
        self.start()

    def get_downloader(self) -> BaseDownloader:
        download_type = settings.downloader.type
        package_path = f".client.{download_type}"
        downloader = importlib.import_module(package_path, package=__package__)
        return downloader.Downloader()

    async def check_host(self) -> bool:
        try:
            return await self.downloader.check_host()
        except AuthorizationError:
            self.start_login()
            return False


Client = DownloadClient()
