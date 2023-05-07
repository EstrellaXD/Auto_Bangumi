import os
import time
import logging
import asyncio

from module.conf import setup_logger, LOG_PATH, RSSLink, VERSION

from module.core import DownloadClient
from module.manager import Renamer, FullSeasonGet
from module.rss import RSSAnalyser
from module.models import Config


logger = logging.getLogger(__name__)


def reset_log():
    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)


async def rss_loop(
    rss_link: str,
    settings: Config,
):
    with RSSAnalyser(settings) as rss:
        rss.rss_to_datas(rss_link)
    if settings.bangumi_manage.eps_complete:
        with FullSeasonGet(settings) as season:
            season.eps_complete()
    await asyncio.sleep(settings.program.sleep_time)


async def rename_loop(renamer: Renamer, wait_time: int = 360):
    renamer.rename()
    await asyncio.sleep(wait_time)


def show_info():
    with open("icon", "r") as f:
        for line in f.readlines():
            logger.info(line.strip("\n"))
    logger.info(
        f"Version {VERSION}  Author: EstrellaXD Twitter: https://twitter.com/Estrella_Pan"
    )
    logger.info("GitHub: https://github.com/EstrellaXD/Auto_Bangumi/")
    logger.info("Starting AutoBangumi...")
