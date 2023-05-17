import os.path

from module.downloader import DownloadClient
from module.network import RequestContent
from module.conf import settings, DATA_PATH


class Checker:
    def __init__(self):
        pass

    def check_renamer(self) -> bool:
        if self.check_downloader() and\
                settings.bangumi_manage.enable:
            return True
        else:
            return False

    def check_analyser(self) -> bool:
        if self.check_torrents() and\
                self.check_downloader() and\
                settings.rss_parser.enable:
            return True
        else:
            return False

    @staticmethod
    def check_downloader() -> bool:
        with DownloadClient() as client:
            if client.authed:
                return True
            else:
                return False

    @staticmethod
    def check_torrents() -> bool:
        with RequestContent() as req:
            try:
                torrents = req.get_torrents(settings.rss_link)
                if torrents:
                    return True
            except AttributeError:
                pass
        return False

    @staticmethod
    def check_first_run() -> bool:
        if os.path.exists(DATA_PATH):
            return False
        else:
            return True
