import os.path

from module.downloader import DownloadClient
from module.network import RequestContent
from module.conf import settings, DATA_PATH


class Checker:
    def __init__(self):
        pass

    def check_renamer(self) -> bool:
        if self.check_downloader() and settings.bangumi_manage.enable:
            return True
        else:
            return False

    def check_analyser(self) -> bool:
        if self.check_downloader() and settings.rss_parser.enable:
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
                torrents = req.get_torrents(settings.rss_link, retry=2)
                if torrents:
                    return True
            except AttributeError:
                link = f"https://mikanani.me/RSS/MyBangumi?token={settings.rss_parser.token}"
                if req.get_torrents(link):
                    return True
        return False

    @staticmethod
    def check_first_run() -> bool:
        token_exist = False if settings.rss_parser.token in ["", "token"] else True
        if token_exist:
            return False
        else:
            return True
