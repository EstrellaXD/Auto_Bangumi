import os
import time
import logging

from module.conf import setup_logger, LOG_PATH, RSSLink, VERSION

from module.core import DownloadClient
from module.manager import Renamer, FullSeasonGet
from module.rss import RSSAnalyser
from module.models import Config


logger = logging.getLogger(__name__)


def reset_log():
    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)


def main_process(rss_link: str, download_client: DownloadClient, _settings: Config):
    rename = Renamer(download_client, _settings)
    rss_analyser = RSSAnalyser(_settings)
    while True:
        times = 0
        if _settings.rss_parser.enable:
            extra_data = rss_analyser.run(rss_link=rss_link)
            download_client.add_rules(extra_data, rss_link)
        if _settings.bangumi_manage.eps_complete:
            FullSeasonGet(settings=_settings).eps_complete(download_client)
        logger.info("Running....")
        while times < _settings.program.rename_times:
            if _settings.bangumi_manage.enable:
                rename.rename()
            times += 1
            time.sleep(_settings.program.sleep_time / _settings.program.rename_times)


def show_info():
    with open("icon", "r") as f:
        for line in f.readlines():
            logger.info(line.strip("\n"))
    logger.info(f"Version {VERSION}  Author: EstrellaXD Twitter: https://twitter.com/Estrella_Pan")
    logger.info("GitHub: https://github.com/EstrellaXD/Auto_Bangumi/")
    logger.info("Starting AutoBangumi...")


def run(settings: Config):
    # 初始化
    rss_link = RSSLink()
    reset_log()
    setup_logger()
    show_info()
    if settings.rss_parser.token in ["", "token", None]:
        logger.error("Please set your RSS token in config file.")
        exit(1)
    download_client = DownloadClient(settings)
    download_client.auth()
    download_client.init_downloader()
    download_client.rss_feed(rss_link)
    # 主程序循环
    main_process(rss_link, download_client, settings)
