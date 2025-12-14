import asyncio
import logging

from module.database import Database
from module.downloader import Client as download_client
from models import Bangumi, Torrent
from module.utils import event_bus
from module.utils.events import Event, EventBus, EventType

logger = logging.getLogger(__name__)


class DownloadCheckMonitor:
    """下载检查监控器

    检查种子是否真的传给了下载客户端，并获取真实的下载UID
    """

    def __init__(self):
        self._event_bus: EventBus = event_bus
        self._shutdown: bool = False

    def initialize(self) -> None:
        """初始化下载检查监控器，订阅下载检查事件"""
        self._shutdown = False
        self._event_bus.subscribe(EventType.DOWNLOAD_CHECK, self.handle_download_check)
        logger.info("[DownloadCheckMonitor] 已注册 DownloadCheckMonitor 事件处理器")
        logger.info("[DownloadCheckMonitor] 下载检查监控器已初始化")

    async def handle_download_check(self, event: Event) -> None:
        """处理下载检查事件

        Args:
            event: 下载检查事件，包含 torrent, bangumi 和 hash_list 信息
        """
        torrent = event.data.get("torrent")
        bangumi = event.data.get("bangumi")
        hash_list = event.data.get("hash_list", [])

        if not torrent or not bangumi:
            logger.warning("[DownloadCheckMonitor] 事件数据不完整")
            return

        if not hash_list:
            logger.warning(f"[DownloadCheckMonitor] 种子 {torrent.name} 没有提供 hash 列表")
            return

        logger.debug(f"[DownloadCheckMonitor] 开始检查种子: {torrent.name}, hash候选: {hash_list}")

        # 检查哪个 hash 真的在下载客户端中
        try:
            real_hash = await self._find_real_hash(hash_list)

            #TODO: NONE 的情况下我该怎么处理呢,也就是说我发了,但是下载客户端那边说没有
            if not real_hash:
                logger.warning(f"[DownloadCheckMonitor] 未找到种子 {torrent.name} 的真实hash，可能添加失败")
                return

            logger.info(f"[DownloadCheckMonitor] 种子 {torrent.name} 真实hash: {real_hash}")

            # 更新种子的 download_uid
            torrent.download_uid = real_hash

            # 保存到数据库
            try:
                with Database() as database:
                    database.torrent.add(torrent)
                    logger.debug(f"[DownloadCheckMonitor] 已保存种子到数据库: {torrent.name}")
            except Exception as e:
                logger.error(f"[DownloadCheckMonitor] 保存种子到数据库失败: {e}")
                return

            # 发布下载开始事件
            await self._publish_download_started(torrent, bangumi)
        except Exception as e:
            logger.error(f"[DownloadCheckMonitor] 处理下载检查事件时出错: {e}")

    async def _find_real_hash(self, hash_list: list[str]) -> str | None:
        """查找真实存在于下载客户端的 hash

        Args:
            hash_list: 候选 hash 列表
            torrent_name: 种子名称（用于日志）

        Returns:
            真实的 hash，如果都不存在则返回 None
        """
        # 等待一小段时间，确保种子已经添加到下载客户端
        await asyncio.sleep(5)
        last_exception = None

        for hash_value in hash_list:
            if not hash_value:
                continue

            logger.debug(f"[DownloadCheckMonitor] 检查 hash: {hash_value}")
            for _ in range(3):
                # 尝试从下载客户端获取种子信息
                if download_client.downloader_error:
                    logger.warning(f"[DownloadCheckMonitor] 下载客户端不可用，跳过检查 hash: {hash_value}")
                    break
                try:
                    info = await download_client.get_torrent_info(hash_value)
                    last_exception = None
                    if info:
                        logger.info(f"[DownloadCheckMonitor] 找到真实hash: {hash_value}")
                        return hash_value
                    else:
                        logger.debug(f"[DownloadCheckMonitor] hash {hash_value} 不存在于下载客户端")
                        break
                except Exception as e:
                    logger.warning(f"[DownloadCheckMonitor] 检查 hash {hash_value} 时出错: {e}")
                    await asyncio.sleep(10)

        if last_exception:
            logger.error(f"[DownloadCheckMonitor] 检查 hash 时遇到错误: {last_exception}")
            raise last_exception
        return None

    async def _publish_download_started(self, torrent: Torrent, bangumi: Bangumi) -> None:
        """发布下载开始事件

        Args:
            torrent: 种子信息
            bangumi: 番剧信息
        """
        if not self._event_bus:
            logger.warning("[DownloadCheckMonitor] EventBus 未设置，无法发布事件")
            return

        try:
            event = Event(
                type=EventType.DOWNLOAD_STARTED,
                data={"torrent": torrent, "bangumi": bangumi},
            )

            asyncio.create_task(self._event_bus.publish(event))
            logger.debug(f"[DownloadCheckMonitor] 已发布下载开始事件: {torrent.name}")

        except Exception as e:
            logger.error(f"[DownloadCheckMonitor] 发布事件失败: {e}")

    async def shutdown(self) -> None:
        """关闭监控器"""
        self._shutdown = True

        # 取消对事件总线的订阅
        self._event_bus.unsubscribe(EventType.DOWNLOAD_CHECK, self.handle_download_check)
        logger.info("[DownloadCheckMonitor] 取消对下载检查事件的订阅")
        logger.info("[DownloadCheckMonitor] 下载检查监控器已关闭")


download_check_monitor = DownloadCheckMonitor()
