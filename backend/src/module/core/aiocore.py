import asyncio
import logging
from abc import abstractmethod

from module.conf import settings
from module.manager import Renamer, eps_complete
from module.rss import RSSEngine
from module.downloader import AsyncDownloadController

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
        task = asyncio.create_task(self.rename_task_loop(),name="renamer_loop")
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
        task = asyncio.create_task(self.rss_task_loop(),name="rss_loop"
                            )
        self.tasks.append(task)

    async def rss_task_loop(self):
        while True:
            task = asyncio.create_task(self.rss_task())
            self.tasks.append(task)
            await asyncio.sleep(settings.program.rss_time)
            self.tasks.remove(task)

    async def rss_task(self):
        rss_engine = RSSEngine()
        await rss_engine.refresh_all_rss()
        if settings.bangumi_manage.eps_complete:
            await eps_complete()

class AsyncDownload(AsyncProgram):
    def __init__(self) -> None:
        super().__init__()
        self.engine = RSSEngine()

    async def run(self):
        await self.stop()
        task = asyncio.create_task(self.download_task_loop(),name="download_loop")
        self.tasks.append(task)

    async def download_task_loop(self):
        while True:
            await self.download_task()

    async def download_task(self):
        downloader = AsyncDownloadController()
        await downloader.download()

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
