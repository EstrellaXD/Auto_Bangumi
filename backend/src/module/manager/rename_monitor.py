import asyncio
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
        self._initialized:bool = False
        # 存储活跃的重命名任务 {torrent_hash: asyncio.Task}
        self.active_rename_tasks: dict[str, asyncio.Task] = {}

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

        # 检查是否已经重命名了
        # TODO: 如果用户在下载完之前改了番剧信息，可能会导致重命名错误
        if not torrent or not bangumi:
            logger.warning("[RenameMonitor] 事件数据不完整")
            return

        if not torrent.download_uid:
            logger.warning(f"[RenameMonitor] 种子 {torrent.name} 没有下载UID")
            return

        torrent_hash = torrent.download_uid

        # 检查是否已有相同种子的重命名任务在运行
        if torrent_hash in self.active_rename_tasks:
            old_task = self.active_rename_tasks[torrent_hash]
            if not old_task.done():
                logger.info(f"[RenameMonitor] 取消之前的重命名任务: {torrent.name}")
                old_task.cancel()
                try:
                    await old_task
                except asyncio.CancelledError:
                    logger.debug(f"[RenameMonitor] 之前的重命名任务已取消: {torrent.name}")

        # 创建新的重命名任务
        task = asyncio.create_task(
            self._execute_rename(torrent, bangumi),
            name=f"rename_{torrent_hash}"
        )
        
        self.active_rename_tasks[torrent_hash] = task
        logger.info(f"[RenameMonitor] 开始新的重命名任务: {torrent.name}")

    async def _execute_rename(self, torrent: Torrent, bangumi: Bangumi) -> None:
        """执行重命名任务的内部方法

        Args:
            torrent: 种子信息
            bangumi: 番剧信息
        """
        if self._renamer is None:
            logger.error("[RenameMonitor] 重命名器未初始化")
            return

        torrent_hash = torrent.download_uid
        try:
            logger.info(f"[RenameMonitor] 执行重命名: {torrent.name}")

            # 执行重命名
            await self._renamer.rename_torrent(torrent, bangumi)

        except asyncio.CancelledError:
            logger.info(f"[RenameMonitor] 重命名任务被取消: {torrent.name}")
            raise
        except Exception as e:
            logger.error(f"[RenameMonitor] 重命名失败: {torrent.name} - {e}")
        finally:
            # 清理任务
            if torrent_hash and torrent_hash in self.active_rename_tasks:
                self.active_rename_tasks.pop(torrent_hash, None)
                logger.debug(f"[RenameMonitor] 清理重命名任务: {torrent.name}")

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
        """关闭重命名监控器，取消所有活跃的重命名任务"""
        if not self.active_rename_tasks:
            logger.info("[RenameMonitor] 重命名监控器已关闭")
            return

        logger.info(f"[RenameMonitor] 关闭监控器，取消 {len(self.active_rename_tasks)} 个活跃任务")
        
        # 取消所有活跃任务
        for task in self.active_rename_tasks.values():
            if not task.done():
                task.cancel()

        # 等待所有任务完成
        if self.active_rename_tasks:
            try:
                await asyncio.gather(
                    *self.active_rename_tasks.values(), 
                    return_exceptions=True
                )
            except Exception as e:
                logger.error(f"[RenameMonitor] 等待任务完成失败: {e}")

        # 清空任务字典
        self.active_rename_tasks.clear()
        logger.info("[RenameMonitor] 重命名监控器已关闭")

    def get_active_tasks_count(self) -> int:
        """获取活跃任务数量"""
        return len(self.active_rename_tasks)

    def get_active_tasks_info(self) -> dict[str, str]:
        """获取活跃任务信息"""
        return {
            torrent_hash: f"Task-{task.get_name()}" 
            for torrent_hash, task in self.active_rename_tasks.items()
            if not task.done()
        }
