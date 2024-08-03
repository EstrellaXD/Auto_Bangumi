import asyncio
import logging
from abc import abstractmethod

from module.conf import settings
from module.database import Database
from module.downloader import DownloadClient
from module.manager import Renamer
from module.models import Bangumi, Torrent
from module.rss import RSSAnalyser, RSSEngine

logger = logging.getLogger(__name__)


class AsyncProgram:
    def __init__(self):
        self.tasks: list[asyncio.Task[None]] = []

    @abstractmethod
    async def run(self):
        pass

    async def stop(self):
        for task in self.tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"{task.get_name()} has canceled")


class AsyncRenamer(AsyncProgram):
    def __init__(self):
        super().__init__()
        self.renamer = Renamer()

    async def run(self):
        await self.stop()
        task = asyncio.create_task(self.rename_task_loop())
        self.tasks.append(task)

    async def rename_task(self):
        renamer = Renamer()
        task = asyncio.create_task(renamer.rename())
        self.tasks.append(task)
        await task
        self.tasks.remove(task)

    async def rename_task_loop(self):
        while True:
            task = asyncio.create_task(self.rename_task())
            self.tasks.append(task)
            await asyncio.sleep(settings.program.rename_time)
            self.tasks.remove(task)


class AsyncRSS(AsyncProgram):
    def __init__(self) -> None:
        super().__init__()
        self.engine = RSSEngine()

    async def run(self):
        await self.stop()
        task = asyncio.create_task(self.rss_task_loop())
        self.tasks.append(task)

    async def rss_task_loop(self):
        while True:
            task = asyncio.create_task(self.rss_task())
            self.tasks.append(task)
            await asyncio.sleep(settings.program.rss_time)
            self.tasks.remove(task)

    async def rss_task(self):
        rss_engine = RSSEngine()
        rss_items = rss_engine.get_active_rss()
        # # 拉取所有的rss
        # 先更新一下database,看看有没有什么新的动漫
        bangumi_database_update_tasks = []
        for rss_item in rss_items:
            bangumi_database_update_tasks.append(
                RSSAnalyser().rss_to_data(rss_item)
            )
        await asyncio.gather(*bangumi_database_update_tasks)

            # 重新拉取一遍 TODO: 要改一下

        async with DownloadClient() as download_client:
            await rss_engine.refresh_all_rss(download_client)


if __name__ == "__main__":
    import asyncio

    from module.conf import setup_logger

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    settings.log.debug_enable = True
    setup_logger()

    asyncio.run(AsyncRenamer().rename_task_loop())
