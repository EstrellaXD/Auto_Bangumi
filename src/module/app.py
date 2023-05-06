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
    rss_analyser: RSSAnalyser,
    download_client: DownloadClient,
    season_get: FullSeasonGet,
    eps_complete: bool = False,
    wait_time: int = 7200,
):
    datas = rss_analyser.run(rss_link)
    if datas:
        download_client.add_rules(datas, rss_link)
        if eps_complete:
            season_get.eps_complete(datas, download_client)
    await asyncio.sleep(wait_time)


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
