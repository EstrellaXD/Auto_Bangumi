from ast import arg
import os
import time
import logging

from conf import settings
from argument_parser import parse
from log import setup_logger
from utils import json_config

from core.rss_collector import RSSCollector
from core.download_client import DownloadClient
from core.renamer import Renamer


logger = logging.getLogger(__name__)


def load_data_file():
    info_path = settings.info_path
    if not os.path.exists(info_path):
        bangumi_data = {
            "rss_link": settings.rss_link,
            "data_version": settings.data_version,
            "bangumi_info": []
        }
    else:
        bangumi_data = json_config.load(info_path)
        if bangumi_data["data_version"] != settings.data_version or bangumi_data["rss_link"] != settings.rss_link:
            bangumi_data["bangumi_info"] = []
            bangumi_data["rss_link"] = settings.rss_link
    return bangumi_data


def save_data_file(bangumi_data):
    info_path = settings.info_path
    json_config.save(info_path, bangumi_data)


def run():
    args = parse()
    # from const_dev import DEV_SETTINGS
    # settings.init(DEV_SETTINGS)
    if args.debug:
        try:
            from const_dev import DEV_SETTINGS
        except ModuleNotFoundError:
            logger.debug("Please copy `const_dev.py` to `const_dev.py` to use custom settings")
        settings.init(DEV_SETTINGS)
    else:
        # init_switch()
        settings.init()
    setup_logger()
    time.sleep(3)
    download_client = DownloadClient()
    download_client.init_downloader()
    download_client.rss_feed()
    rss_collector = RSSCollector()
    renamer = Renamer(download_client)
    loop = 0
    while True:
        bangumi_data = load_data_file()
        try:
            rss_collector.collect(bangumi_data)
            if settings.enable_eps_complete:
                download_client.eps_collect(bangumi_data["bangumi_info"])
            download_client.add_rules(bangumi_data["bangumi_info"])
            save_data_file(bangumi_data)
            if loop == 0:
                logger.info(f"Waiting for downloading torrents...")
                time.sleep(600)
            renamer.run()
            time.sleep(settings.sleep_time)
        except Exception as e:
            if args.debug:
                raise e
            logger.exception(e)
        loop += 1


if __name__ == "__main__":
    run()
