import threading
from concurrent.futures import ThreadPoolExecutor

from module.conf import settings
from module.downloader import DownloadClient
from module.manager import Renamer, eps_complete
from module.notification import Notifier
from module.rss import RSSAnalyser, RSSEngine

from .status import ProgramStatus


class RSSThread(ProgramStatus):
    def __init__(self):
        super().__init__()
        self._rss_thread = threading.Thread(
            target=self.rss_loop,
        )
        self.analyser = RSSAnalyser()

    def rss_loop(self):
        while not self.stop_event.is_set():
            with DownloadClient() as client, RSSEngine() as engine:
                # Analyse RSS
                rss_list = engine.rss.search_aggregate()
                for rss in rss_list:
                    self.analyser.rss_to_data(rss, engine)
                # Run RSS Engine
                engine.refresh_rss(client)
            if settings.bangumi_manage.eps_complete:
                eps_complete()
            self.stop_event.wait(settings.program.rss_time)

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
                notifier = Notifier(
                    settings.notification.type,
                    config=settings.notification.dict(exclude={"type", "enable"}),
                )
                with ThreadPoolExecutor(max_workers=2) as worker:
                    worker.map(notifier.send, renamed_info)

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
