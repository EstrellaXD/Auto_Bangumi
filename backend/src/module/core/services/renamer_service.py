import logging
from typing import Any
import asyncio

from module.conf import settings
from module.core.services import BaseService
from module.database import Database
from module.manager.renamer import Renamer
from module.utils.events import Event, EventType, event_bus

logger = logging.getLogger(__name__)


class RenamerService(BaseService):
    """重命名服务 - 检查已下载但未重命名的种子并发布重命名事件"""

    def __init__(self):
        super().__init__()
        self._renamer: Renamer = Renamer()
        self.enable = settings.bangumi_manage.enable

    async def _setup(self) -> None:
        """初始化重命名器"""
        self._renamer = Renamer()

    async def initialize(self) -> None:
        await super().initialize()
        self.enable = settings.bangumi_manage.enable

    def get_task_config(self) -> dict[str, Any]:
        """获取重命名任务配置"""
        return {
            "name": "renamer_check",
            "interval": 600,  # 转换为秒
            "enabled": self.enable,
        }

    async def execute(self) -> None:
        """执行重命名检查任务"""
        if not self._renamer:
            logger.error("[RenamerService] 重命名器未初始化")
            return

        try:
            # 查询已下载但未重命名的种子
            with Database() as db:
                unrenamed_torrents = db.torrent.search_downloaded_unrenamed()

            if not unrenamed_torrents:
                logger.debug("[RenamerService] 没有需要重命名的种子")
                return

            logger.info(
                f"[RenamerService] 发现 {len(unrenamed_torrents)} 个需要重命名的种子"
            )

            # 为每个种子发布下载完成事件，触发重命名流程
            for torrent in unrenamed_torrents:
                await self._publish_download_completed_event(torrent)

        except Exception as e:
            logger.error(f"[RenamerService] 执行失败: {e}")
            raise

    async def _publish_download_completed_event(self, torrent) -> None:
        """发布下载完成事件

        Args:
            torrent: 种子信息
        """
        try:
            # 获取对应的番剧信息
            with Database() as db:
                bangumi = db.torrent_to_bangumi(torrent)

            if not bangumi:
                logger.warning(
                    f"[RenamerService] 无法找到种子 {torrent.name} 对应的番剧信息"
                )
                return

            event = Event(
                type=EventType.DOWNLOAD_STARTED,
                data={
                    "torrent": torrent,
                    "bangumi": bangumi,
                    "download_uid": torrent.download_uid,
                    "name": torrent.name,
                },
            )

            asyncio.create_task(
                event_bus.publish(event)  # 异步执行事件发布
            )  # 异步执行重命名
            logger.debug(f"[RenamerService] 已发布重命名事件: {torrent.name}")

        except Exception as e:
            logger.error(f"[RenamerService] 发布重命名事件失败: {e}")
