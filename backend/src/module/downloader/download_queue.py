import asyncio
import logging

from module.database import Database, engine
from module.downloader.client.expection import AuthorizationError
from module.downloader.download_client import DownloadClient
from module.models import Bangumi, Torrent

MIN_SIZE = 10
logger = logging.getLogger(__name__)
queue: asyncio.Queue[tuple[Torrent, Bangumi]] = asyncio.Queue()
download_add_event = asyncio.Event()
download_len_event = asyncio.Event()


class DownloadQueue:
    def __init__(self) -> None:
        self.queue = queue

    async def add_torrents(self, torrents: list[Torrent], bangumi: Bangumi):
        for torrent in torrents:
            self.add(torrent, bangumi)
        if self.queue.qsize() > MIN_SIZE:
            download_len_event.set()

    def add(self, torrent: Torrent, bangumi: Bangumi):
        self.queue.put_nowait((torrent, bangumi))
        logger.debug(
            f"[Download Queue] add {bangumi.official_title}, torrent url = {torrent.name}"
        )
        download_add_event.set()


class AsyncDownloadController:
    async def download(self):
        await download_add_event.wait()  # 等待事件被设置
        download_add_event.clear()  # 重置事件
        # 等待足够数量的元素或超时
        try:
            async with DownloadClient() as client:
                try:
                    await asyncio.wait_for(download_len_event.wait(), timeout=3)
                except asyncio.TimeoutError:
                    logger.debug(
                        "[Download Controller] Timeout reached. reach all available items"
                    )
                # 取出队列中所有现有的元素
                download_len_event.clear()
                tasks = []
                torrents = []
                while not queue.empty():
                    torrent, bangumi = queue.get_nowait()
                    logging.debug(f"[Download Queue] start download {torrent.name}")
                    torrents.append(torrent)
                    tasks.append(client.add_torrent(torrent, bangumi))
                    queue.task_done()
                await asyncio.gather(*tasks, return_exceptions=True)
            with Database() as database:
                database.torrent.add_all(torrents)
        except AuthorizationError as e:
            logger.error(f"[Download Controller] AuthorizationError: {e}")
            await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(AsyncDownloadController().download())
