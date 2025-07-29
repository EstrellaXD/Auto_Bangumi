import logging

from module.utils.events import Event, EventType, EventBus
from module.manager import Renamer
from module.models import Bangumi, Torrent
from module.database import Database

logger = logging.getLogger(__name__)


class RenameMonitor:
    """重命名监控器

    监听下载完成事件，触发重命名操作，并在完成后发布重命名完成事件
    """

    def __init__(self, event_bus: EventBus | None = None):
        self._event_bus: EventBus | None = event_bus
        self._renamer: Renamer | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """初始化重命名器"""
        if not self._initialized:
            self._renamer = Renamer()
            self._initialized = True
            logger.info("[RenameMonitor] 初始化完成")

    async def handle_download_completed(self, event: Event) -> None:
        """处理下载完成事件

        Args:
            event: 下载完成事件，包含torrent和bangumi信息
        """
        if not self._initialized or not self._renamer:
            logger.error("[RenameMonitor] 服务未初始化")
            return

        torrent = event.data.get("torrent")
        bangumi = event.data.get("bangumi")

        if not torrent or not bangumi:
            logger.warning("[RenameMonitor] 事件数据不完整")
            return

        try:
            logger.info(f"[RenameMonitor] 开始重命名: {torrent.name}")

            # 执行重命名
            await self._renamer.rename_torrent(torrent, bangumi)
            # 更新种子状态为已重命名
            torrent.renamed = True
            torrent.save_path = bangumi.save_path  # 更新保存路径
            with Database() as db:
                db.torrent.update(torrent)

            # 发布重命名完成事件
            await self._publish_rename_completed(torrent, bangumi)

        except Exception as e:
            logger.error(f"[RenameMonitor] 重命名失败: {torrent.name} - {e}")

    async def _publish_rename_completed(
        self, torrent: Torrent, bangumi: Bangumi
    ) -> None:
        """发布重命名完成事件

        Args:
            torrent: 种子信息
            bangumi: 番剧信息
        """
        if not self._event_bus:
            logger.warning("[RenameMonitor] EventBus 未设置，无法发布事件")
            return

        try:
            event = Event(
                type=EventType.RENAME_COMPLETED,
                data={"torrent": torrent, "bangumi": bangumi},
            )

            await self._event_bus.publish(event)
            logger.info(f"[RenameMonitor] 已发布重命名完成事件: {torrent.name}")

        except Exception as e:
            logger.error(f"[RenameMonitor] 发布事件失败: {e}")

    async def shutdown(self) -> None:
        """关闭重命名监控器"""
        logger.info("[RenameMonitor] 重命名监控器已关闭")
