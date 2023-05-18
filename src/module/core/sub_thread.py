import threading

from .status import ProgramStatus

from module.rss import RSSAnalyser, add_rules
from module.manager import Renamer, FullSeasonGet
from module.conf import settings


class RSSThread(ProgramStatus):
    def __init__(self):
        super().__init__()
        self._rss_thread = threading.Thread(
            target=self.rss_loop,
        )
        self._rss_analyser = RSSAnalyser()

    def rss_loop(self):
        while not self.stop_event.is_set():
            self._rss_analyser.run()
            add_rules()
            if settings.bangumi_manage.eps_complete:
                with FullSeasonGet() as full_season_get:
                    full_season_get.eps_complete()
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
                renamer.rename()
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
