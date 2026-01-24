import logging
from pathlib import Path

import httpx

from module.conf import VERSION, settings
from module.models import Config
from module.update import version_check

logger = logging.getLogger(__name__)


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
    def check_first_run() -> bool:
        if Path("config/.setup_complete").exists():
            return False
        return settings.dict() == Config().dict()

    @staticmethod
    def check_version() -> tuple[bool, int | None]:
        return version_check()

    @staticmethod
    def check_database() -> bool:
        db_path = Path("data/data.db")
        if not db_path.exists():
            return False
        else:
            return True

    @staticmethod
    async def check_downloader() -> bool:
        from module.downloader import DownloadClient
        try:
            url = (
                f"http://{settings.downloader.host}"
                if "://" not in settings.downloader.host
                else f"{settings.downloader.host}"
            )
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(url)
            if "qbittorrent" in response.text.lower() or "vuetorrent" in response.text.lower():
                async with DownloadClient() as dl_client:
                    if dl_client.authed:
                        return True
                    else:
                        return False
            else:
                return False
        except httpx.TimeoutException:
            logger.error("[Checker] Downloader connect timeout.")
            return False
        except httpx.ConnectError:
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
        else:
            img_path.mkdir()
            return False
