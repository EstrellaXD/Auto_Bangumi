import asyncio
import logging
from typing import TYPE_CHECKING, Any
from typing_extensions import override

from module.database import Database, engine
from module.downloader import Client as client
from module.downloader.download_queue import download_queue
from module.utils import event_bus
from module.utils.events import Event, EventBus, EventType, ServiceException
from models import Bangumi, Torrent
from .base_services import BaseService

logger = logging.getLogger(__name__)


class DownloadService(BaseService):
    def __init__(self):
        super().__init__()
        self._event_bus: EventBus = event_bus

    @override
    async def _setup(self) -> None:
        """初始化下载服务"""
        logger.debug("[DownloadService] 下载服务已初始化")

    def get_task_config(self) -> dict[str, Any]:
        """获取下载任务配置"""
        return {
            "name": "download_process",
            "interval": 5,
            "enabled": True,
        }

    @override
    async def execute(self) -> None:
        """执行下载任务"""
        try:
            await self._download()
            logger.debug("[DownloadService] 下载任务完成")
        except TimeoutError:
            logger.error("[DownloadService] 无法连接到下载器")
            raise
        except Exception as e:
            logger.error(f"[DownloadService] 执行失败: {e}")
            raise ServiceException("download", f"执行失败: {e}")

    async def _download(self) -> None:
        """从队列获取并执行下载任务"""
        # 确保下载客户端已登录,没有的话就直接返回
        if not await client.wait_for_login():
            return

        queue_size = download_queue.qsize()
        if queue_size == 0:
            return

        torrent, bangumi = download_queue.get_nowait()
        download_queue.task_done()
        logging.debug(f"[DownloadService] start download {torrent.name}")

        # 执行下载任务
        try:
            hash_list = await client.add_torrent(torrent, bangumi)
            # 处理下载结果并发布检查事件
            if hash_list:  # 下载请求已发送，hash列表不为空
                # 发布下载检查事件，让 DownloadCheckMonitor 验证真实hash
                await self._publish_download_check(torrent, bangumi, hash_list)
            else:
                logger.warning(f"[DownloadService] 下载种子失败，未返回hash: {torrent.name}")
        except Exception as e:
            logger.error(f"[DownloadService] 下载种子失败: {torrent.name} - {e}")

    async def _publish_download_check(self, torrent: Torrent, bangumi: Bangumi, hash_list: list[str]) -> None:
        """发布下载检查事件

        Args:
            torrent: 种子信息
            bangumi: 番剧信息
            hash_list: 候选hash列表
        """
        if not self._event_bus:
            logger.warning("[DownloadService] EventBus 未设置，无法发布事件")
            return

        try:
            event = Event(
                type=EventType.DOWNLOAD_CHECK,
                data={"torrent": torrent, "bangumi": bangumi, "hash_list": hash_list},
            )

            asyncio.create_task(self._event_bus.publish(event))
            logger.debug(f"[DownloadService] 已发布下载检查事件: {torrent.name}, hash候选: {hash_list}")

        except Exception as e:
            logger.error(f"[DownloadService] 发布下载检查事件失败: {e}")

    async def cleanup(self) -> None:
        """清理下载客户端"""
        try:
            from module.downloader import Client

            await Client.stop()
            self._initialized: bool = False
            logger.debug("[DownloadService] 下载客户端已重启")
        except Exception as e:
            logger.error(f"[DownloadService] 清理失败: {e}")
            raise ServiceException("download", f"清理失败: {e}")
