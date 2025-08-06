import asyncio
import logging

from module.database import Database
from module.downloader.download_client import Client as download_client
from module.models import Bangumi, Torrent
from module.utils import event_bus
from module.utils.events import Event, EventBus, EventType

logger = logging.getLogger(__name__)


class DownloadMonitor:
    """下载监控器

    监控下载客户端中种子的下载状态，当检测到下载完成时发布事件
    """

    def __init__(self):
        # 存储活跃的监控任务 {torrent_hash: asyncio.Task}
        self.monitoring_tasks: dict[str, asyncio.Task] = {}
        self._shutdown: bool = False
        self._event_bus: EventBus = event_bus

    def initialize(self) -> None:
        """初始化下载监控器，订阅下载开始事件"""
        # 订阅下载开始事件
        self._shutdown = False
        self._event_bus.subscribe(
            EventType.DOWNLOAD_STARTED, self.handle_download_started
        )

        logger.info("[DownloadMonitor] 已注册 DownloadMonitor 事件处理器")
        logger.info("[DownloadMonitor] 下载监控器已初始化")

    def calculate_sleep_time(self, eta: int) -> int:
        """根据剩余时间计算睡眠间隔

        Args:
            eta: 预计剩余时间（秒）

        Returns:
            睡眠间隔（秒）
        """
        if eta <= 0:  # 已完成或无效
            return 10
        elif eta < 60:  # 小于1分钟，每10秒检查
            return 10
        elif eta < 300:  # 小于5分钟，每30秒检查
            return 30
        elif eta < 1800:  # 小于30分钟，每2分钟检查
            return 120
        else:  # 超过30分钟，每5分钟检查
            return 300

    async def handle_download_started(self, event: Event) -> None:
        """处理下载开始事件

        Args:
            event: 下载开始事件，包含torrent和bangumi信息
        """
        torrent = event.data.get("torrent")
        bangumi = event.data.get("bangumi")

        if not torrent or not bangumi:
            logger.warning("[DownloadMonitor] 事件数据不完整")
            return

        if not torrent.download_uid:
            logger.warning(f"[DownloadMonitor] 种子 {torrent.name} 没有下载UID")
            return

        # 等待30秒让种子准备好，避免过早删除
        logger.debug(f"[DownloadMonitor] 等待60秒让种子准备: {torrent.name}")
        await asyncio.sleep(60)
        await self.start_monitoring(torrent.download_uid, bangumi, torrent)

    async def start_monitoring(
        self, torrent_duid: str, bangumi: Bangumi, torrent: Torrent
    ) -> None:
        """开始监控指定种子的下载状态

        Args:
            torrent_hash: 种子哈希值
            bangumi: 番剧信息
            torrent: 种子信息
        """
        if torrent_duid in self.monitoring_tasks:
            logger.debug(f"[DownloadMonitor] 种子 {torrent_duid} 已在监控中")
            return

        # 创建监控任务
        task = asyncio.create_task(
            self.monitor_torrent(bangumi, torrent),
            name=f"monitor_{torrent_duid}",
        )

        self.monitoring_tasks[torrent_duid] = task
        # logger.debug(f"[DownloadMonitor] 开始监控种子: {torrent.name}")

    async def monitor_torrent(self, bangumi: Bangumi, torrent: Torrent) -> None:
        """监控单个种子的下载状态

        Args:
            torrent_hash: 种子哈希值
            bangumi: 番剧信息
            torrent: 种子信息
        """
        try:
            torrent_hash = torrent.download_uid
            logger.debug(f"[DownloadMonitor] 开始监控种子: {torrent.name} ({torrent_hash})")
            if not torrent_hash:
                logger.warning(f"[DownloadMonitor] 种子 {torrent.name} 没有下载UID")
                return

            retry_count = 0
            while not self._shutdown:
                # 获取种子信息
                info = await download_client.get_torrent_info(torrent_hash)
                logger.debug(
                    f"[DownloadMonitor] 获取种子信息: {torrent.name} - {torrent_hash}"
                )

                if not info:
                    logger.warning(
                        f"[DownloadMonitor] 无法获取种子信息: {torrent_hash}，将从数据库删除对应记录"
                    )
                    # 从数据库删除对应的torrent记录
                    if retry_count < 3:
                        retry_count += 1
                        logger.debug(
                            f"[DownloadMonitor] 获取种子信息失败，将等待60秒后重试: {torrent.name} ({retry_count}/3)"
                        )
                        await asyncio.sleep(60)  # 等待60秒后重试
                        continue
                    else:
                        logger.debug(
                            f"[DownloadMonitor] 重试次数超过3次，删除种子记录: {torrent.name}"
                        )
                        try:
                            with Database() as db:
                                db.torrent.delete_by_url(torrent.url)
                                logger.debug(
                                    f"[DownloadMonitor] 已从数据库删除种子记录: {torrent.name}"
                                )
                        except Exception as e:
                            logger.error(f"[DownloadMonitor] 删除数据库记录失败: {e}")
                        break

                # 更新数据库中torrent的downloaded状态
                elif not torrent.downloaded:
                    logger.debug(
                        f"[DownloadMonitor] 种子 {torrent.name} 下载状态: 下载中"
                    )
                    try:
                        with Database() as db:
                            logger.debug(
                                f"[DownloadMonitor] 更新种子下载状态: {torrent.name} - {torrent_hash}"
                            )
                            if torrent_item := db.torrent.search_by_duid(torrent_hash):
                                if not torrent_item.downloaded:
                                    torrent_item.downloaded = True
                                    db.torrent.add(torrent_item)
                                    logger.debug(
                                        f"[DownloadMonitor] 已更新种子下载状态: {torrent.name}"
                                    )
                    except Exception as e:
                        logger.error(f"[DownloadMonitor] 更新种子下载状态失败: {e}")

                # 检查是否下载完成
                if info.completed != 0:
                    logger.debug(
                        f"[DownloadMonitor] 种子 {torrent.name} 下载状态: 已完成 {info.completed}"
                    )

                    # 发布下载完成事件
                    await self._publish_download_completed(torrent, bangumi)
                    break

                # 根据ETA智能睡眠
                if info.eta is not None:
                    sleep_time = self.calculate_sleep_time(info.eta)
                    logger.debug(
                        f"[DownloadMonitor] 种子 {torrent.name} ETA: {info.eta}s, 下次检查: {sleep_time}s"
                    )
                else:
                    sleep_time = 60  # 默认1分钟

                await asyncio.sleep(sleep_time)

        except asyncio.CancelledError:
            logger.debug(f"[DownloadMonitor] 监控任务被取消: {torrent.name}")
        except Exception as e:
            logger.error(f"[DownloadMonitor] 监控种子失败: {torrent.name} - {e}")
        finally:
            # 清理任务
            if torrent_hash:
                self.monitoring_tasks.pop(torrent_hash, None)
                logger.debug(f"[DownloadMonitor] 清理监控任务: {torrent.name}")

    async def _publish_download_completed(
        self, torrent: Torrent, bangumi: Bangumi
    ) -> None:
        """发布下载完成事件

        Args:
            torrent: 种子信息
            bangumi: 番剧信息
        """
        if not self._event_bus:
            logger.warning("[DownloadMonitor] EventBus 未设置，无法发布事件")
            return

        try:
            event = Event(
                type=EventType.DOWNLOAD_COMPLETED,
                data={"torrent": torrent, "bangumi": bangumi},
            )

            asyncio.create_task(self._event_bus.publish(event))
            logger.debug(f"[DownloadMonitor] 已发布下载完成事件: {torrent.name}")

        except Exception as e:
            logger.error(f"[DownloadMonitor] 发布事件失败: {e}")

    def stop_monitoring(self, torrent_hash: str) -> bool:
        """停止监控指定种子

        Args:
            torrent_hash: 种子哈希值

        Returns:
            是否成功停止监控
        """
        task = self.monitoring_tasks.get(torrent_hash)
        if task:
            task.cancel()
            logger.debug(f"[DownloadMonitor] 停止监控种子: {torrent_hash}")
            return True
        return False

    async def shutdown(self) -> None:
        """关闭监控器，取消所有监控任务"""
        self._shutdown = True

        # 取消对事件总线的订阅
        self._event_bus.unsubscribe(
            EventType.DOWNLOAD_STARTED, self.handle_download_started
        )
        logger.info("[DownloadMonitor] 取消对下载开始事件的订阅")
        if not self.monitoring_tasks:
            return

        logger.info(
            f"[DownloadMonitor] 关闭监控器，取消 {len(self.monitoring_tasks)} 个任务"
        )

        # 取消所有任务
        for task in self.monitoring_tasks.values():
            if not task.done():
                task.cancel()

        # 等待所有任务完成
        if self.monitoring_tasks:
            await asyncio.gather(
                *self.monitoring_tasks.values(), return_exceptions=True
            )

        self.monitoring_tasks.clear()
        logger.info("[DownloadMonitor] 监控器已关闭")

    def get_monitoring_status(self) -> dict:
        """获取监控状态

        Returns:
            监控状态信息
        """
        return {
            "active_tasks": len(self.monitoring_tasks),
            "monitoring_hashes": list(self.monitoring_tasks.keys()),
            "shutdown": self._shutdown,
        }


download_monitor = DownloadMonitor()
