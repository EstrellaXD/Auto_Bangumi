import os.path
import threading
import asyncio

from module.checker import Checker
from module.conf import DATA_PATH


class ProgramStatus(Checker):
    def __init__(self):
        super().__init__()
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self._downloader_status = False
        self._torrents_status = False
        self.event = asyncio.Event()

    @property
    def is_running(self):
        return not self.stop_event.is_set()

    @property
    def is_stopped(self):
        return self.stop_event.is_set()

    @property
    def downloader_status(self):
        if not self._downloader_status:
            self._downloader_status = self.check_downloader()
        return self._downloader_status

    @property
    def torrents_status(self):
        if not self._torrents_status:
            self._torrents_status = self.check_torrents()
        return self._torrents_status

    @property
    def enable_rss(self):
        return self.check_analyser()

    @property
    def enable_renamer(self):
        return self.check_renamer()

    @property
    def first_run(self):
        return self.check_first_run()

    @property
    def legacy_data(self):
        return os.path.exists("data/data.json")
