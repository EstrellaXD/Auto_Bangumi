import asyncio
import logging
from typing import Any

import aiolimiter
import httpx

from module.exceptions import AuthorizationError, ForbiddenError, InvalidCredentialsError
from models import Torrent, TorrentDownloadInfo
from module.network import RequestContent
from models.config import Downloader as DownloaderConfig
from module.utils import gen_save_path
from module.utils.torrent import torrent_to_link

from .client import BaseDownloader, QbittorrentDownloader
from .download_queue import download_queue

logger = logging.getLogger(__name__)


class DownloadClient:
    """
    下载器客户端
    处理所有下载器相关操作
    """

    def __init__(self, config: DownloaderConfig):
        # self.downloader: BaseDownloader | None = None
        # 用于等待登陆完成
        self.login_success_event: asyncio.Event = asyncio.Event()
        self.login_timeout: int = 5  # 5秒超时

        # API 限流和任务控制
        self._api_lock: asyncio.Lock = asyncio.Lock()
        self._api_cancel_event: asyncio.Event = asyncio.Event()
        self.api_interval: float = 0.2  # 默认间隔，将在initialize后更新
        self.is_authenticating: bool = False  # 重置认证状态
        self.downloader_error: bool = False  # 下载器错误状态
        self.config: DownloaderConfig = config
        self.get_downloader(config.type)
        self.initialize()
        self.limiter: aiolimiter.AsyncLimiter = aiolimiter.AsyncLimiter(1, self.api_interval)

    def get_downloader(self, dtype: str):
        """获取下载器实例"""
        downloader_type = dtype
        if downloader_type == "qbittorrent":
            self.downloader: BaseDownloader = QbittorrentDownloader()
            logger.debug(f"[Downloader Client] Using downloader: {downloader_type}")
        else:
            logger.debug(f"[Downloader Client] Using default downloader: qbittorrent")
            self.downloader: BaseDownloader = QbittorrentDownloader()

    def initialize(self):
        # 根据设置动态获取下载器
        if not self.downloader:
            raise ValueError("Downloader initialization failed")
        # 初始化下载器
        self.downloader.initialize(self.config)
        # 更新API间隔
        self.api_interval = self.downloader.api_interval

    async def login(self) -> bool:
        """一次性登录尝试，不重试"""
        if not self.downloader:
            logger.error("[Downloader Client] 下载器错误，无法登录")
            return False
        self.login_success_event.clear()  # 重置事件状态
        self.is_authenticating = True  # 设置正在认证状态
        logger.debug("[Downloader Client] attempting authentication")
        # // 网络错误的话可以再去试试, 密码错误就算了
        try:
            if await self.downloader.auth():
                self.login_success_event.set()  # 设置认证成功事件
                return True
        except InvalidCredentialsError or ForbiddenError as e:
            # 对于无效的账号密码或被ban了, 不再进行登陆
            logger.error(f"[Downloader Client] authentication failed: {e}")
            self.downloader_error = True
            return False
            # 保持 login_success_event 为 clear 状态，表示认证失败
        except Exception as e:
            logger.error(f"[Downloader Client] network error: {e}")
            return False
        finally:
            self.is_authenticating = False
        return False

    async def wait_for_login(self) -> bool:
        """等待认证完成，返回是否可以继续API调用"""
        # 如果下载器处于错误状态，直接返回False
        if self.downloader_error:
            return False
        # 如果已认证成功，直接返回True
        if self.login_success_event.is_set():
            return True

        # 如果正在认证中（login_task存在且未完成），等待认证完成
        if self.is_authenticating:
            try:
                await asyncio.wait_for(self.login_success_event.wait(), self.login_timeout)
                return self.login_success_event.is_set()
            except asyncio.TimeoutError:
                logger.warning("[Downloader Client] Authentication wait timeout")
                return False

        # 如果未认证且未在认证中，启动认证
        # 这里发为 True防止重复认证
        self.is_authenticating = True  # 设置正在认证状态
        return await self.login()


    async def get_torrents_info(
        self, category="Bangumi", status_filter="completed", tag=None, limit=0
    ) -> list[dict[str, Any]]:
        await asyncio.wait_for(self.limiter.acquire(), timeout=30)
        if not await self.wait_for_login():
            return []  # 登录失败时返回空列表

        try:
            resp = await self.downloader.torrents_info(
                category=category,
                status_filter=status_filter,
                tag=tag,
                limit=limit,
            )
            return resp
        except AuthorizationError:
            self.login_success_event.clear()
            return []

    async def add_torrent(self, torrent: Torrent, bangumi) -> list[str]:
        await asyncio.wait_for(self.limiter.acquire(), timeout=30)
        if not await self.wait_for_login():
            return []  # 登录失败时返回False

        torrent_url = torrent.url
        logging.debug(f"[Downloader] send url {torrent_url}to downloader ")
        # 如果种子不是以 magnet 开头的, 把种子下载下来
        torrent_content = None
        if not torrent_url.startswith("magnet:"):
            try:
                async with RequestContent() as req:
                    torrent_content= await req.get_content(torrent_url)
                    hashs = torrent_to_link(torrent_content)
            except httpx.RequestError as e:
                # // 404 说明链接有错,不是一个有效的种子链接, 会见于mikan的部分种子
                if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 404:
                    logger.error(f"[Downloader] Torrent URL not found (404): {torrent_url}")
                raise
        else:
            hashs = [torrent.url]
        try:
            result = await self.downloader.add(
                hashs=hashs,
                torrent_content=torrent_content,
                save_path=gen_save_path(self.config.path, bangumi),
            )
            return result
        except AuthorizationError:
            self.login_success_event.clear()
            # TODO: 重试太多了怎么办?
            # https://mikanani.me/Home/Episode/4294fd53bcd1bfe2ff3b5796004ee3ccb1ba0d0e  这是个死种
            download_queue.add(torrent, bangumi)  # 重新放回队列
            logger.debug(f"[Downloader] Add torrent failed, re-adding to queue: {torrent.name}")
            return []

    async def move_torrent(self, hashes: list[str] | str, location: str) -> bool:
        await asyncio.wait_for(self.limiter.acquire(), timeout=30)
        if not await self.wait_for_login():
            return False  # 登录失败时返回False
        try:
            result = await self.downloader.move(hashes=hashes, new_location=location)
            if result:
                logger.info(f"[Downloader] Move torrents {hashes} to {location}")
                return True
            else:
                logger.warning(f"[Downloader] Move torrents {hashes} to {location} failed")
                return False
        except AuthorizationError:
            self.login_success_event.clear()
        return False

    # async def set_category(self, hashes, category):
    #     await self.downloader.set_category(hashes, category)

    async def rename_torrent_file(self, torrent_hash: str, old_path: str, new_path: str) -> bool:
        await asyncio.wait_for(self.limiter.acquire(), timeout=30)
        if not await self.wait_for_login():
            return False  # 登录失败时返回False

        try:
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
            self.login_success_event.clear()
        return False

    async def delete_torrent(self, hashes: list[str] | str) -> bool:
        await asyncio.wait_for(self.limiter.acquire(), timeout=30)
        if not await self.wait_for_login():
            return False  # 登录失败时返回False

        try:
            result = await self.downloader.delete(hashes)
            if result:
                logger.debug(f"[Downloader] Remove torrents {hashes}.")
                return True
            else:
                logger.warning(f"[Downloader] Remove torrents {hashes} failed")
                return False
        except AuthorizationError:
            self.login_success_event.clear()
        return False

    async def get_torrent_info(self, hash: str) -> TorrentDownloadInfo | None:
        await asyncio.wait_for(self.limiter.acquire(), timeout=30)
        if not await self.wait_for_login():
            return None

        try:
            result = await self.downloader.torrent_info(hash)
            logger.debug(f"[Downloader] find torrents {hash} info. result: {result is not None}")
            return result
        except AuthorizationError:
            self.login_success_event.clear()
            raise

    async def get_torrent_files(self, _hash: str) -> list[str] | None:
        # 获取种子文件列表
        # 文件夹举例
        # LKSUB][Make Heroine ga Oosugiru!][01-12][720P]/[LKSUB][Make Heroine ga Oosugiru!][01][720P].mp4
        await asyncio.wait_for(self.limiter.acquire(), timeout=30)
        if not await self.wait_for_login():
            return []  # 登录失败时返回空列表

        try:
            return await self.downloader.get_torrent_files(_hash)
        except AuthorizationError:
            self.login_success_event.clear()
        return []

    def start(self):
        self.reset_api_cancel()  # 重置API取消状态

        # 重置所有相关状态，确保重启后正常工作
        self.login_success_event.clear()
        self.is_authenticating = False

        # 重新创建锁，确保锁状态正确
        self._api_lock = asyncio.Lock()

        logger.debug("[Download Client] 所有状态已重置")
        # 下次 API 调用时会自动登录

    def cancel_all_api_calls(self):
        """取消所有等待中的API调用"""
        self._api_cancel_event.set()

    def reset_api_cancel(self):
        """重置API取消状态，允许新的API调用"""
        self._api_cancel_event.clear()

    async def stop(self):
        logger.info("[Download Client] Stopping download client")
        self.cancel_all_api_calls()  # 先取消所有API调用
        if self.login_success_event.is_set():
            await self.downloader.logout()

    async def check_host(self) -> bool:
        return await self.downloader.check_host()
