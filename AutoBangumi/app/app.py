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
        bangumi_data = {"rss_link": "", "bangumi_info": []}
    else:
        bangumi_data = json_config.load(info_path)
    return bangumi_data


def save_data_file(bangumi_data):
    info_path = settings.info_path
    json_config.save(info_path, bangumi_data)


def run():
    args = parse()
    if args.debug:
        from const_dev import DEV_SETTINGS

        settings.init(DEV_SETTINGS)
    else:
        settings.init()
    setup_logger()
    bangumi_data = load_data_file()
    download_client = DownloadClient()
    download_client.rss_feed()
    rss_collector = RSSCollector()
    renamer = Renamer(download_client)
    while True:
        try:
            rss_collector.collect(bangumi_data)
            download_client.add_rules(bangumi_data["bangumi_info"])
            download_client.eps_collect(bangumi_data["bangumi_info"])
            renamer.run()
            save_data_file(bangumi_data)
            time.sleep(settings.sleep_time)
        except Exception as e:
            if args.debug:
                raise e
            logger.exception(e)


if __name__ == "__main__":
    run()