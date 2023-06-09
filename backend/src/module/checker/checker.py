from module.conf import settings
from module.downloader import DownloadClient
from module.models import Config
from module.network import RequestContent


class Checker:
    def __init__(self):
        pass

    @staticmethod
    def check_renamer() -> bool:
        if settings.bangumi_manage.enable:
            return True
        else:
            return False

    @staticmethod
    def check_analyser() -> bool:
        if settings.rss_parser.enable:
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
        if settings.dict() == Config().dict():
            return True
        else:
            return False
