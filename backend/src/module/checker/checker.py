import os
from pathlib import Path

from module.conf import settings, VERSION
from module.downloader import DownloadClient
from module.models import Config
from module.network import RequestContent
from module.update import version_check


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
    def check_first_run() -> bool:
        if settings.dict() == Config().dict():
            return True
        else:
            return False

    @staticmethod
    def check_version() -> bool:
        return version_check()

    @staticmethod
    def check_database() -> bool:
        db_path = Path("data/data.db")
        if not db_path.exists():
            return False
        else:
            return True


if __name__ == "__main__":
    print(Checker().check_version())
