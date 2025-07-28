import asyncio
import logging

from module.database import Database
from module.core.events import Event, EventType, EventBus
from module.downloader.download_client import Client as client
from module.models import Bangumi, Torrent

logger = logging.getLogger(__name__)
queue: asyncio.Queue[tuple[Torrent, Bangumi]] = asyncio.Queue()


class DownloadQueue:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[tuple[Torrent, Bangumi]] = queue

    async def add_torrents(self, torrents: list[Torrent], bangumi: Bangumi):
        for torrent in torrents:
            self.add(torrent, bangumi)

    def add(self, torrent: Torrent, bangumi: Bangumi):
        self.queue.put_nowait((torrent, bangumi))
        logger.debug(
            f"[Download Queue] add to queue {bangumi.official_title}, torrent name = {torrent.name} ,torrent url = {torrent.url}"
        )


class DownloadController:
    def __init__(self):
        self._download_monitor = None
        self._event_bus = None

    def set_download_monitor(self, monitor):
        """设置下载监控器"""
        self._download_monitor = monitor
    
    def set_event_bus(self, event_bus: EventBus):
        """设置事件总线"""
        self._event_bus = event_bus

    # 10秒拿5个
    async def download(self):
        logger.debug("[Download Controller] start download")
        tasks = []
        torrents = []
        torrent_bangumi_pairs = []

        # 一次取五个torrent
        for _ in range(min(queue.qsize(), 5)):
            torrent, bangumi = queue.get_nowait()
            queue.task_done()
            logging.debug(f"[Download Controller] start download {torrent.name}")
            torrents.append(torrent)
            torrent_bangumi_pairs.append((torrent, bangumi))
            tasks.append(client.add_torrent(torrent, bangumi))

        # 执行下载任务
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理下载结果并发布事件
        for i, result in enumerate(results):
            torrent, bangumi = torrent_bangumi_pairs[i]
            
            if result is True:  # 下载成功
                if torrent.download_guid:  # 有下载哈希
                    try:
                        # 发布下载开始事件
                        await self._publish_download_started(torrent, bangumi)
                        logger.debug(f"[Download Controller] 已发布下载开始事件: {torrent.name}")
                        
                        # 启动监控（如果有监控器）
                        if self._download_monitor:
                            await self._download_monitor.start_monitoring(
                                torrent.download_guid, bangumi, torrent
                            )
                            logger.debug(f"[Download Controller] 已启动监控: {torrent.name}")
                    except Exception as e:
                        logger.error(f"[Download Controller] 处理下载成功事件失败: {torrent.name} - {e}")
            elif isinstance(result, Exception):
                logger.error(f"[Download Controller] 下载失败: {torrent.name} - {result}")
        # 保存到数据库
        with Database() as database:
            database.torrent.add_all(torrents)

    async def _publish_download_started(self, torrent: Torrent, bangumi: Bangumi) -> None:
        """发布下载开始事件
        
        Args:
            torrent: 种子信息
            bangumi: 番剧信息
        """
        if not self._event_bus:
            logger.warning("[Download Controller] EventBus 未设置，无法发布事件")
            return
            
        try:
            event = Event(
                type=EventType.DOWNLOAD_STARTED,
                data={'torrent': torrent, 'bangumi': bangumi}
            )
            
            await self._event_bus.publish(event)
            logger.debug(f"[Download Controller] 已发布下载开始事件: {torrent.name}")
            
        except Exception as e:
            logger.error(f"[Download Controller] 发布下载开始事件失败: {e}")
