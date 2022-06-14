import os
import time
import logging

from conf.conf import settings
from conf.argument_parser import parse
from conf.log import setup_logger
from utils import json_config

from core.rss_analyser import RSSAnalyser
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
            bangumi_data["data_version"] = settings.data_version
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
    logger.info(f"Version {settings.version}  Author: EstrellaXD Twitter: https://twitter.com/Estrella_Pan")
    logger.info("GitHub: https://github.com/EstrellaXD/Auto_Bangumi/")
    logger.info("Starting AutoBangumi...")





def run():
    # DEBUG 模式初始化
    args = parse()
    if args.debug:
        try:
            from conf.const_dev import DEV_SETTINGS
            settings.init(DEV_SETTINGS)
        except ModuleNotFoundError:
            logger.debug("Please copy `const_dev.py` to `const_dev.py` to use custom settings")
    else:
        settings.init()
    # 初始化
    setup_logger()
    show_info()
    time.sleep(3)
    download_client = DownloadClient()
    download_client.init_downloader()
    if settings.rss_link is None:
        logger.error("Please add RIGHT RSS url.")
        quit()
    download_client.rss_feed()
    rss_analyser = RSSAnalyser()
    rename = Renamer(download_client)
    # 主程序循环
    while True:
        bangumi_data = json_config.load(settings.info_path)
        rss_analyser.rss_to_data(bangumi_data["bangumi_info"])
        download_client.add_rules(bangumi_data["bangumi_info"])


if __name__ == "__main__":
    run()
