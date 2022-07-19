import os
import time
import logging

from __version__ import version
from conf import settings, parse
from conf.log import setup_logger
from utils import json_config

from core import RSSAnalyser, DownloadClient, Renamer, FullSeasonGet


logger = logging.getLogger(__name__)


def reset_log():
    try:
        os.remove(settings.log_path)
    except FileNotFoundError:
        pass


def load_data_file():
    info_path = settings.info_path
    if not os.path.exists(info_path):
        bangumi_data = {
            "rss_link": settings.rss_link,
            "data_version": settings.data_version,
            "bangumi_info": []
        }
        logger.info("Building data information...")
    else:
        bangumi_data = json_config.load(info_path)
        if bangumi_data["data_version"] != settings.data_version or bangumi_data["rss_link"] != settings.rss_link:
            bangumi_data = {
                "rss_link": settings.rss_link,
                "data_version": settings.data_version,
                "bangumi_info": []
            }
            logger.info("Rebuilding data information...")
    return bangumi_data


def save_data_file(bangumi_data):
    info_path = settings.info_path
    json_config.save(info_path, bangumi_data)
    logger.debug("Saved")


def show_info():
    logger.info("                _        ____                                    _ ")
    logger.info("     /\        | |      |  _ \                                  (_)")
    logger.info("    /  \  _   _| |_ ___ | |_) | __ _ _ __   __ _ _   _ _ __ ___  _ ")
    logger.info("   / /\ \| | | | __/ _ \|  _ < / _` | '_ \ / _` | | | | '_ ` _ \| |")
    logger.info("  / ____ \ |_| | || (_) | |_) | (_| | | | | (_| | |_| | | | | | | |")
    logger.info(" /_/    \_\__,_|\__\___/|____/ \__,_|_| |_|\__, |\__,_|_| |_| |_|_|")
    logger.info("                                            __/ |                  ")
    logger.info("                                           |___/                   ")
    logger.info(f"Version {version}  Author: EstrellaXD Twitter: https://twitter.com/Estrella_Pan")
    logger.info("GitHub: https://github.com/EstrellaXD/Auto_Bangumi/")
    logger.info("Starting AutoBangumi...")


def main_process(bangumi_data, download_client: DownloadClient):
    rename = Renamer(download_client)
    if settings.reset_folder:
        rename.set_folder()
    rss_analyser = RSSAnalyser()
    while True:
        times = 0
        if settings.enable_rss_collector:
            rss_analyser.run(bangumi_data["bangumi_info"], download_client)
        if settings.eps_complete:
            FullSeasonGet().eps_complete(bangumi_data["bangumi_info"], download_client)
        logger.info("Running....")
        save_data_file(bangumi_data)
        while times < settings.times:
            if settings.enable_rename:
                rename.run()
            times += 1
            time.sleep(settings.sleep_time/settings.times)


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
    reset_log()
    setup_logger()
    show_info()
    download_client = DownloadClient()
    download_client.init_downloader()
    if settings.rss_link is None:
        logger.error("Please add RIGHT RSS url.")
        quit()
    download_client.rss_feed()
    bangumi_data = load_data_file()
    # 主程序循环
    main_process(bangumi_data, download_client)


if __name__ == "__main__":
    run()
