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
            "first_run": True,
            "bangumi_info": []
        }
    else:
        bangumi_data = json_config.load(info_path)
        if bangumi_data["data_version"] != settings.data_version or bangumi_data["rss_link"] != settings.rss_link:
            bangumi_data["bangumi_info"] = []
            bangumi_data["first_run"] = True
            bangumi_data["rss_link"] = settings.rss_link
            logger.info("Rebuilding data information...")
    return bangumi_data


def save_data_file(bangumi_data):
    info_path = settings.info_path
    json_config.save(info_path, bangumi_data)


def show_info():
    logger.info("                _        ____                                    _ ")
    logger.info("     /\        | |      |  _ \                                  (_)")
    logger.info("    /  \  _   _| |_ ___ | |_) | __ _ _ __   __ _ _   _ _ __ ___  _ ")
    logger.info("   / /\ \| | | | __/ _ \|  _ < / _` | '_ \ / _` | | | | '_ ` _ \| |")
    logger.info("  / ____ \ |_| | || (_) | |_) | (_| | | | | (_| | |_| | | | | | | |")
    logger.info(" /_/    \_\__,_|\__\___/|____/ \__,_|_| |_|\__, |\__,_|_| |_| |_|_|")
    logger.info("                                            __/ |                  ")
    logger.info("                                           |___/                   ")
    logger.info("Version 2.4.9  Author: EstrellaXD Twitter: https://twitter.com/Estrella_Pan")
    logger.info("GitHub: https://github.com/EstrellaXD/Auto_Bangumi/")
    logger.info("Starting AutoBangumi...")


def run():
    args = parse()
    if args.debug:
        try:
            from const_dev import DEV_SETTINGS
        except ModuleNotFoundError:
            logger.debug("Please copy `const_dev.py` to `const_dev.py` to use custom settings")
        settings.init(DEV_SETTINGS)
    else:
        settings.init()
    setup_logger()
    show_info()
    time.sleep(3)
    download_client = DownloadClient()
    download_client.init_downloader()
    if settings.rss_link is None:
        logger.error("Please add RIGHT RSS url.")
        quit()
    download_client.rss_feed()
    rss_collector = RSSCollector()
    renamer = Renamer(download_client)
    while True:
        bangumi_data = load_data_file()
        try:
            rss_collector.collect(bangumi_data)
            if settings.enable_eps_complete:
                download_client.eps_collect(bangumi_data["bangumi_info"])
            download_client.add_rules(bangumi_data["bangumi_info"])
            if bangumi_data["first_run"]:
                logger.info(f"Waiting for downloading torrents...")
                time.sleep(600)
                bangumi_data["first_run"] = False
            save_data_file(bangumi_data)
            renamer.run()
            time.sleep(settings.sleep_time)
        except Exception as e:
            if args.debug:
                raise e
            logger.exception(e)


if __name__ == "__main__":
    run()
