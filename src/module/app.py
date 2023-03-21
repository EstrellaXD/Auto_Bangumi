import os
import time
import logging

from module.conf import settings, LOG_PATH, DATA_PATH
from module.utils import json_config

from module.core import DownloadClient
from module.manager import Renamer, FullSeasonGet
from module.rss import RSSAnalyser


logger = logging.getLogger(__name__)


def reset_log():
    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)


def load_data_file():
    if not os.path.exists(DATA_PATH):
        bangumi_data = {
            "rss_link": settings.rss_parser.link,
            "data_version": settings.program.data_version,
            "bangumi_info": []
        }
        logger.info("Building data information...")
    else:
        bangumi_data = json_config.load(DATA_PATH)
        if bangumi_data["data_version"] != settings.program.data_version or bangumi_data["rss_link"] != settings.rss_parser.link:
            bangumi_data = {
                "rss_link": settings.rss_parser.link,
                "data_version": settings.program.data_version,
                "bangumi_info": []
            }
            logger.info("Rebuilding data information...")
    return bangumi_data


def save_data_file(bangumi_data):
    json_config.save(DATA_PATH, bangumi_data)
    logger.debug("Saved")


def main_process(bangumi_data, download_client: DownloadClient):
    rename = Renamer(download_client)
    rss_analyser = RSSAnalyser()
    while True:
        times = 0
        if settings.rss_parser.enable:
            rss_analyser.run(bangumi_data["bangumi_info"], download_client)
        if settings.bangumi_manage.eps_complete and bangumi_data["bangumi_info"] != []:
            FullSeasonGet().eps_complete(bangumi_data["bangumi_info"], download_client)
        logger.info("Running....")
        save_data_file(bangumi_data)
        while times < settings.program.times:
            if settings.bangumi_manage.enable:
                rename.run()
            times += 1
            time.sleep(settings.program.sleep_time / settings.program.times)


def run():
    # 初始化
    reset_log()
    download_client = DownloadClient()
    download_client.init_downloader()
    if "://" not in settings.rss_parser.link:
        logger.error("Please add RIGHT RSS url.")
        os._exit(1)
    download_client.rss_feed()
    bangumi_data = load_data_file()
    # 主程序循环
    main_process(bangumi_data, download_client)
