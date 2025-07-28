import asyncio
import logging

from module.database import Database

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


class AsyncDownloadController:
    def __init__(self):
        self._download_monitor = None

    def set_download_monitor(self, monitor):
        """设置下载监控器"""
        self._download_monitor = monitor

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

        # 处理下载结果并启动监控
        for i, result in enumerate(results):
            if result is True and self._download_monitor:  # 下载成功
                torrent, bangumi = torrent_bangumi_pairs[i]
                if torrent.download_guid:  # 有下载哈希
                    try:
                        await self._download_monitor.start_monitoring(
                            torrent.download_guid, bangumi, torrent
                        )
                        logger.debug(
                            f"[Download Controller] 已启动监控: {torrent.name}"
                        )
                    except Exception as e:
                        logger.error(
                            f"[Download Controller] 启动监控失败: {torrent.name} - {e}"
                        )
            elif isinstance(result, Exception):
                logger.error(
                    f"[Download Controller] 下载失败: {torrents[i].name} - {result}"
                )
        # 保存到数据库
        with Database() as database:
            database.torrent.add_all(torrents)
