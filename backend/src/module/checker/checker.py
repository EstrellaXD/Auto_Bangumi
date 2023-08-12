import os

from module.conf import settings, VERSION
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
    def check_first_run() -> bool:
        if settings.dict() == Config().dict():
            return True
        else:
            return False

    @staticmethod
    def check_version() -> bool:
        if not os.path.exists("config/version.info"):
            with open("config/version.info", "w+") as f:
                f.writelines(VERSION)
            return True
        with open("config/version.info", "r+") as f:
            legacy_version = f.readlines()[-1]
            if VERSION == legacy_version:
                return False
            else:
                f.writelines(VERSION)
                return True


if __name__ == "__main__":
    print(Checker().check_version())
