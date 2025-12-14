import asyncio
import logging

from models import Bangumi, Torrent

logger = logging.getLogger(__name__)


class DownloadQueue:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[tuple[Torrent, Bangumi]] = asyncio.Queue()
        self._added_torrents: set[str] = set()  # 用于快速查重

    async def add_torrents(self, torrents: list[Torrent], bangumi: Bangumi):
        for torrent in torrents:
            self.add(torrent, bangumi)

    def add(self, torrent: Torrent, bangumi: Bangumi):
        # 这是最早加入 torrent.bangumi_official_title, torrent.bangumi_season, torrent.rss_link 的地方
        # 要查重,torrent.url 是唯一的
        if torrent.url in self._added_torrents:
            logger.debug(f"[Download Queue] {torrent.name} 已经在下载队列中，跳过添加")
            return
        torrent.bangumi_official_title = bangumi.official_title
        torrent.bangumi_season = bangumi.season
        torrent.rss_link = bangumi.rss_link
        self.queue.put_nowait((torrent, bangumi))
        self._added_torrents.add(torrent.url)
        logger.debug(
            f"[Download Queue] add to queue {bangumi.official_title}, torrent name = {torrent.name} ,torrent url = {torrent.url}"
        )

    def qsize(self) -> int:
        """获取队列大小"""
        return self.queue.qsize()

    def get_nowait(self) -> tuple[Torrent, Bangumi]:
        """获取队列中的下一个任务，不阻塞"""
        t = self.queue.get_nowait()
        self._added_torrents.discard(t[0].url)
        return t

    def task_done(self):
        """标记队列中的一个任务已完成"""
        self.queue.task_done()

    async def join(self):
        """等待队列中的所有任务完成"""
        await self.queue.join()


download_queue = DownloadQueue()
