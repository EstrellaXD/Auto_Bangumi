import asyncio
import logging

from module.database import Database, engine
from module.downloader.download_client import Client as client
from module.utils import event_bus
from module.utils.events import Event, EventBus, EventType
from module.models import Bangumi, Torrent

from .download_queue import download_queue

logger = logging.getLogger(__name__)


class DownloadController:
    def __init__(self):
        self._event_bus: EventBus = event_bus

    # 10秒拿5个
    async def download(self):
        if client.login_success_event.is_set() is False:
            if client.login_task is None:
                logger.warning(
                    "[Download Controller] 正在尝试登录下载客户端，请稍候..."
                )
                client.login_task = asyncio.create_task(client.login())
            return
        queue_size = download_queue.qsize()
        if queue_size == 0:
            return

        tasks = []
        torrents = []
        torrent_bangumi_pairs = []

        # 一次取五个torrent
        batch_size = min(queue_size, 5)

        for i in range(batch_size):
            torrent, bangumi = download_queue.get_nowait()

            download_queue.task_done()
            logging.debug(f"[Download Controller] start download {torrent.name}")
            torrents.append(torrent)
            torrent_bangumi_pairs.append((torrent, bangumi))
            tasks.append(client.add_torrent(torrent, bangumi))
            # 更新种子信息

        # 执行下载任务
        results = await asyncio.gather(*tasks)

        # 处理下载结果并发布事件
        # 保存到数据库

        with Database(engine) as database:
            for torrent in torrents:
                if torrent.download_uid:  # 有下载哈希
                    database.torrent.add(torrent)
        for i, result in enumerate(results):
            torrent, bangumi = torrent_bangumi_pairs[i]

            if result is True:  # 下载成功
                if torrent.download_uid:  # 有下载哈希
                    # 发布下载开始事件
                    await self._publish_download_started(torrent, bangumi)
            elif isinstance(result, Exception):
                logger.error(
                    f"[Download Controller] 下载失败: {torrent.name} - {result}"
                )

    async def _publish_download_started(
        self, torrent: Torrent, bangumi: Bangumi
    ) -> None:
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
                data={"torrent": torrent, "bangumi": bangumi},
            )

            asyncio.create_task(self._event_bus.publish(event))
            logger.debug(f"[Download Controller] 已发布下载开始事件: {torrent.name}")

        except Exception as e:
            logger.error(f"[Download Controller] 发布下载开始事件失败: {e}")
