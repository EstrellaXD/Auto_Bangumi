import asyncio

from module.conf import settings
from module.downloader import DownloadClient
from module.manager import Renamer, eps_complete
from module.notification import PostNotification
from module.rss import RSSAnalyser, RSSEngine

from .status import ProgramStatus


class RSSThread(ProgramStatus):
    def __init__(self):
        super().__init__()
        self._rss_task: asyncio.Task | None = None
        self.analyser = RSSAnalyser()

    async def rss_loop(self):
        while not self.stop_event.is_set():
            async with DownloadClient() as client:
                with RSSEngine() as engine:
                    # Analyse RSS
                    rss_list = engine.rss.search_aggregate()
                    for rss in rss_list:
                        await self.analyser.rss_to_data(rss, engine)
                    # Run RSS Engine
                    await engine.refresh_rss(client)
            if settings.bangumi_manage.eps_complete:
                await eps_complete()
            try:
                await asyncio.wait_for(
                    self.stop_event.wait(),
                    timeout=settings.program.rss_time,
                )
            except asyncio.TimeoutError:
                pass

    def rss_start(self):
        self._rss_task = asyncio.create_task(self.rss_loop())

    async def rss_stop(self):
        if self._rss_task and not self._rss_task.done():
            self.stop_event.set()
            self._rss_task.cancel()
            try:
                await self._rss_task
            except asyncio.CancelledError:
                pass
            self._rss_task = None


class RenameThread(ProgramStatus):
    def __init__(self):
        super().__init__()
        self._rename_task: asyncio.Task | None = None

    async def rename_loop(self):
        while not self.stop_event.is_set():
            async with Renamer() as renamer:
                renamed_info = await renamer.rename()
            if settings.notification.enable and renamed_info:
                async with PostNotification() as notifier:
                    await asyncio.gather(
                        *[notifier.send_msg(info) for info in renamed_info]
                    )
            try:
                await asyncio.wait_for(
                    self.stop_event.wait(),
                    timeout=settings.program.rename_time,
                )
            except asyncio.TimeoutError:
                pass

    def rename_start(self):
        self._rename_task = asyncio.create_task(self.rename_loop())

    async def rename_stop(self):
        if self._rename_task and not self._rename_task.done():
            self.stop_event.set()
            self._rename_task.cancel()
            try:
                await self._rename_task
            except asyncio.CancelledError:
                pass
            self._rename_task = None
