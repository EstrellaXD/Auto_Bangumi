import threading
import time

from module.conf import settings
from module.database import BangumiDatabase
from module.downloader import DownloadClient
from module.manager import Renamer, eps_complete
from module.notification import PostNotification
from module.rss import analyser

from .status import ProgramStatus


class RSSThread(ProgramStatus):
    def __init__(self):
        super().__init__()
        self._rss_thread = threading.Thread(
            target=self.rss_loop,
        )

    def rss_loop(self):
        while not self.stop_event.is_set():
            # Analyse RSS
            with BangumiDatabase() as db:
                new_data = analyser.rss_to_data(rss_link=settings.rss_link, database=db)
                if new_data:
                    db.insert_list(new_data)
                bangumi_list = db.not_added()
                if bangumi_list:
                    with DownloadClient() as client:
                        client.set_rules(bangumi_list)
                    db.update_list(bangumi_list)
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
