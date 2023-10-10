import threading
import time
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
        self._rss_thread = threading.Thread(
            target=self.rss_loop,
        )
        self.analyser = RSSAnalyser()

    async def __loop_mission(self):
        async with RSSEngine() as engine:
            await engine.rss_checker(self.analyser, self.stop_event)

    def rss_loop(self):
        asyncio.run(self.__loop_mission())

    def rss_start(self):
        self.rss_thread.start()

    def rss_stop(self):
        if self._rss_thread.is_alive():
            self._rss_thread.join()

    @property
    def rss_thread(self):
        if not self._rss_thread.is_alive():
            self._rss_thread = threading.Thread(
                target=self.rss_loop,
            )
        return self._rss_thread


class RenameThread(ProgramStatus):
    def __init__(self):
        super().__init__()
        self._rename_thread = threading.Thread(
            target=self.rename_loop,
        )

    def rename_loop(self):
        while not self.stop_event.is_set():
            with Renamer() as renamer:
                renamed_info = renamer.rename()
            if settings.notification.enable:
                with PostNotification() as notifier:
                    for info in renamed_info:
                        notifier.send_msg(info)
                        time.sleep(2)
            self.stop_event.wait(settings.program.rename_time)

    def rename_start(self):
        self.rename_thread.start()

    def rename_stop(self):
        if self._rename_thread.is_alive():
            self._rename_thread.join()

    @property
    def rename_thread(self):
        if not self._rename_thread.is_alive():
            self._rename_thread = threading.Thread(
                target=self.rename_loop,
            )
        return self._rename_thread
