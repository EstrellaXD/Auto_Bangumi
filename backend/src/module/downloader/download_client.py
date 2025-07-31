import asyncio
import importlib
import logging
import time
from functools import wraps
from typing import Any

from module.conf import settings
from module.downloader.client import AuthorizationError, BaseDownloader, Downloader
from module.models import Torrent, TorrentDownloadInfo
from module.utils import gen_save_path

logger = logging.getLogger(__name__)


def api_rate_limit(func):
    """API速率限制装饰器，支持任务取消"""

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        task_id = id(asyncio.current_task())

        # 先添加到等待任务集合，确保能被追踪和取消
        self._waiting_api_tasks.add(task_id)

        try:
            # 在获取锁前先检查是否已被取消
            if self._api_cancel_event.is_set():
                logger.info(f"[API Rate Limit] {func.__name__} cancelled before lock")
                raise asyncio.CancelledError("API call cancelled")

            # 可取消的锁获取 - 等待锁或取消信号
            while True:
                lock_task = asyncio.create_task(self._api_lock.acquire())
                cancel_task = asyncio.create_task(self._api_cancel_event.wait())

                done, pending = await asyncio.wait(
                    [lock_task, cancel_task], return_when=asyncio.FIRST_COMPLETED
                )

                # 取消未完成的任务
                for task in pending:
                    task.cancel()

                # 检查是否被取消
                if self._api_cancel_event.is_set():
                    # 如果锁已经获取，需要释放
                    if lock_task.done() and not lock_task.cancelled():
                        self._api_lock.release()
                    logger.info(
                        f"[API Rate Limit] {func.__name__} cancelled while waiting for lock"
                    )
                    raise asyncio.CancelledError("API call cancelled")

                # 成功获取锁
                break

            try:
                current_time = time.time()
                time_since_last = current_time - self._last_api_call

                if self.api_interval >= 0 and time_since_last < self.api_interval:
                    wait_time = self.api_interval - time_since_last
                    logger.debug(
                        f"[API Rate Limit] {func.__name__} waiting {wait_time:.2f}s"
                    )

                    # 可中断的等待
                    done, pending = await asyncio.wait(
                        [
                            asyncio.create_task(asyncio.sleep(wait_time)),
                            asyncio.create_task(self._api_cancel_event.wait()),
                        ],
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    # 取消未完成的任务
                    for task in pending:
                        task.cancel()

                    # 检查是否被取消
                    if self._api_cancel_event.is_set():
                        logger.info(
                            f"[API Rate Limit] {func.__name__} cancelled during sleep"
                        )
                        raise asyncio.CancelledError("API call cancelled")

                # 调用原函数
                result = await func(self, *args, **kwargs)

                # 更新最后调用时间
                self._last_api_call = time.time()

                return result

            finally:
                # 释放锁
                self._api_lock.release()

        except asyncio.CancelledError:
            logger.info(f"[API Rate Limit] {func.__name__} was cancelled")
            raise
        except Exception as e:
            logger.error(f"[API Rate Limit] {func.__name__} error: {e}")
            raise
        finally:
            # 确保从等待任务集合中移除
            self._waiting_api_tasks.discard(task_id)

    return wrapper


class DownloadClient:
    """
    下载器客户端
    处理所有下载器相关操作, 对错误进行重试, 不对外暴露错误,看起来是正常运行
    """

    def __init__(self):
        self.downloader: BaseDownloader = Downloader()
        # 用于等待登陆完成
        self.login_success_event: asyncio.Event = asyncio.Event()
        self.login_timeout: int = 30  # 30秒超时
        self.login_task: asyncio.Task | None = None

        # API 限流和任务控制
        self._api_lock: asyncio.Lock = asyncio.Lock()
        self._last_api_call: float = 0
        self._api_cancel_event: asyncio.Event = asyncio.Event()
        self._waiting_api_tasks: set[int] = set()  # 追踪等待中的API任务
        self.api_interval: float = -1  # 默认1秒间隔
        self.is_authenticating:bool = False  # 重置认证状态

    async def login(self):
        """一次性登录尝试，不重试"""
        try:
            self.login_success_event.clear()  # 重置事件状态
            self.is_authenticating = True  # 设置正在认证状态
            logger.debug("[Downloader Client] attempting authentication")

            if await self.downloader.auth():
                self.login_success_event.set()  # 设置认证成功事件
                logger.info("[Downloader Client] authentication success")
            else:
                # 保持 login_success_event 为 clear 状态，表示认证失败
                logger.warning("[Downloader Client] authentication failed")

        except Exception as e:
            logger.error(f"[Downloader Client] authentication error: {e}")
            # 保持 login_success_event 为 clear 状态，表示认证失败
        finally:
            self.is_authenticating = False

    async def wait_for_login(self) -> bool:
        """等待认证完成，返回是否可以继续API调用"""
        # 如果已认证成功，直接返回True  
        if self.login_success_event.is_set():
            return True

        # 如果正在认证中（login_task存在且未完成），等待认证完成
        if self.is_authenticating:
            try:
                await asyncio.wait_for(
                    self.login_success_event.wait(), self.login_timeout
                )
                return self.login_success_event.is_set()
            except asyncio.TimeoutError:
                logger.warning("[Downloader Client] Authentication wait timeout")
                return False

        # 如果未认证且未在认证中，启动认证
        self.start_login()

        # 等待这次认证完成
        try:
            await asyncio.wait_for(self.login_success_event.wait(), self.login_timeout)
            return self.login_success_event.is_set()
        except asyncio.TimeoutError:
            logger.warning("[Downloader Client] Authentication timeout")
            return False

    @api_rate_limit
    async def get_torrents_info(
        self, category="Bangumi", status_filter="completed", tag=None, limit=0
    ) -> list[dict[str, Any]]:
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
            self.start_login()
            return []

    @api_rate_limit
    async def add_torrent(self, torrent: Torrent, bangumi) -> bool:
        if not await self.wait_for_login():
            return False  # 登录失败时返回False

        try:
            torrent_file = None
            torrent_url = torrent.url
            logging.debug(f"[Downloader] send url {torrent_url}to downloader ")

            result = await self.downloader.add(
                torrent_urls=torrent_url,
                torrent_file=torrent_file,
                save_path= gen_save_path(settings.downloader.path, bangumi),
                category="Bangumi",
            )
            if result:
                torrent.download_uid = result
                logger.debug(f"[Downloader] Add torrent: {torrent.name}")
                return True
            else:
                logger.warning(
                    f"[Downloader] Torrent added failed: {torrent.name},{torrent.url=}"
                )
        except AuthorizationError:
            self.start_login()
        return False

    @api_rate_limit
    async def move_torrent(self, hashes: list[str] | str, location: str) -> bool:
        if not await self.wait_for_login():
            return False  # 登录失败时返回False

        try:
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

    @api_rate_limit
    async def rename_torrent_file(
        self, torrent_hash: str, old_path: str, new_path: str
    ) -> bool:
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
            self.start_login()
        return False

    @api_rate_limit
    async def delete_torrent(self, hashes: list[str] | str) -> bool:
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
            self.start_login()
        return False

    @api_rate_limit
    async def get_torrent_info(self, hash: str) -> TorrentDownloadInfo|None:
        if not await self.wait_for_login():
            return None

        try:
            result = await self.downloader.torrent_info(hash)
            if result:
                logger.debug(f"[Downloader] find torrents {hash} info.")
                return result
            else:
                logger.warning(f"[Downloader] find torrents {hash} info failed")
        except AuthorizationError:
            self.start_login()
        return None

    @api_rate_limit
    async def get_torrent_files(self, _hash: str) -> list[str] | None:
        # 获取种子文件列表
        # 文件夹举例
        # LKSUB][Make Heroine ga Oosugiru!][01-12][720P]/[LKSUB][Make Heroine ga Oosugiru!][01][720P].mp4
        if not await self.wait_for_login():
            return []  # 登录失败时返回空列表

        try:
            return await self.downloader.get_torrent_files(_hash)
        except AuthorizationError:
            self.start_login()
        return []

    def start_login(self):
        self.login_task = asyncio.create_task(self.login(), name="login")

    def start(self):
        # 判断有没有 login task
        self.start_login()

    def cancel_all_api_calls(self):
        """取消所有等待中的API调用"""
        logger.info(
            f"[Download Client] Cancelling {len(self._waiting_api_tasks)} waiting API calls"
        )
        self._api_cancel_event.set()

    def reset_api_cancel(self):
        """重置API取消状态，允许新的API调用"""
        self._api_cancel_event.clear()

    def get_waiting_api_count(self) -> int:
        """获取等待中的API任务数量"""
        return len(self._waiting_api_tasks)

    async def stop(self):
        logger.info("[Download Client] Stopping download client")
        self.cancel_all_api_calls()  # 先取消所有API调用
        await self.downloader.logout()
        if self.login_task:
            self.login_task.cancel()

    async def restart(self):
        logger.info("[Download Client] Restarting download client")
        await self.stop()
        self.reset_api_cancel()  # 重置API取消状态
        # 重置认证状态，允许重新尝试认证
        self.start()

    async def check_host(self) -> bool:
        return await self.downloader.check_host()


Client = DownloadClient()  # 兼容旧代码


if __name__ == "__main__":
    import asyncio

    from module.conf import setup_logger

    # setup_logger("DEBUG", reset=True)

    download_client = Client
    torrent_hash = "e4d2134ff46ee5b8d729318def73fa19993c36d6"
    async def test_one_time_login():
        info = await download_client.get_torrent_info(torrent_hash)
        print(info)

    asyncio.run(test_one_time_login())
