import asyncio
import logging

from module.database import Database, engine
from module.downloader.client.expection import AuthorizationError
from module.downloader.download_client import Client as client
from module.models import Bangumi, Torrent

MIN_SIZE = 5
logger = logging.getLogger(__name__)
queue: asyncio.Queue[tuple[Torrent, Bangumi]] = asyncio.Queue()
download_add_event = asyncio.Event()
download_len_event = asyncio.Event()


class DownloadQueue:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[tuple[Torrent, Bangumi]] = queue

    async def add_torrents(self, torrents: list[Torrent], bangumi: Bangumi):
        for torrent in torrents:
            self.add(torrent, bangumi)

    def add(self, torrent: Torrent, bangumi: Bangumi):
        self.queue.put_nowait((torrent, bangumi))
        logger.debug(
            f"[Download Queue] add {bangumi.official_title}, torrent name = {torrent.name} ,torrent url = {torrent.url}"
        )
        download_add_event.set()


class AsyncDownloadController:
    # 10秒拿5个
    async def download(self):
        logger.debug("[Download Controller] start download")
        await download_add_event.wait()  # 等待事件被设置
        # 等待足够数量的元素或超时
        tasks = []
        torrents = []
        # 一次取五个torrent
        for _ in range(5):
            if queue.empty():
                download_add_event.clear()  # 重置事件
                # 为空时退出
                break
            torrent, bangumi = queue.get_nowait()
            queue.task_done()
            logging.debug(f"[Download Queue] start download {torrent.name}")
            torrents.append(torrent)
            tasks.append(client.add_torrent(torrent, bangumi))
        await asyncio.gather(*tasks)
        with Database() as database:
            database.torrent.add_all(torrents)


if __name__ == "__main__":
    asyncio.run(AsyncDownloadController().download())
