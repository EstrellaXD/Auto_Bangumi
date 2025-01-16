import logging
from pathlib import Path

import requests

from module.conf import VERSION, settings
from module.downloader import DownloadClient
from module.models import Config
from module.update import version_check

logger = logging.getLogger(__name__)


class Checker:
    def __init__(self):
        pass

    @staticmethod
    def check_renamer() -> bool:
        return bool(settings.bangumi_manage.enable)

    @staticmethod
    def check_analyser() -> bool:
        return bool(settings.rss_parser.enable)

    @staticmethod
    def check_first_run() -> bool:
        return settings.dict() == Config().dict()

    @staticmethod
    def check_version() -> bool:
        return version_check()

    @staticmethod
    def check_database() -> bool:
        db_path = Path("data/data.db")
        return db_path.exists()

    @staticmethod
    def check_downloader() -> bool:
        try:
            url = (
                f"http://{settings.downloader.host}"
                if "://" not in settings.downloader.host
                else f"{settings.downloader.host}"
            )
            response = requests.get(url, timeout=2)
            if (
                "qbittorrent" not in response.text.lower()
                and "vuetorrent" not in response.text.lower()
            ):
                return False
            with DownloadClient() as client:
                return bool(client.authed)
        except requests.exceptions.ReadTimeout:
            logger.error("[Checker] Downloader connect timeout.")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("[Checker] Downloader connect failed.")
            return False
        except Exception as e:
            logger.error(f"[Checker] Downloader connect failed: {e}")
            return False

    @staticmethod
    def check_img_cache() -> bool:
        img_path = Path("data/posters")
        if img_path.exists():
            return True
        img_path.mkdir()
        return False
