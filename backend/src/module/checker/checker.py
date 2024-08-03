import logging
from pathlib import Path

import httpx

from module.conf import VERSION, settings
from module.downloader import DownloadClient
from module.models import Config
from module.network import RequestContent
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

    @staticmethod
    async def check_downloader() -> bool:
        try:
            url = (
                f"http://{settings.downloader.host_}"
                if "://" not in settings.downloader.host_
                else f"{settings.downloader.host_}"
            )

            # response = await RequestContent().get(url, timeout=2)
            # if settings.downloader.type in response.text.lower():
            # 能auth 就算正确, 类型判断无用
            async with DownloadClient() as client:
                if await client.auth():
                    return True
            return False
            # else:
            #     return False
        except httpx.ReadTimeout:
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

if __name__ =="__main__":
    import asyncio
    # print(asyncio.run(Checker().check_downloader()))
