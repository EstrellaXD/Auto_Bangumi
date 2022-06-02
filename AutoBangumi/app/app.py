import os
import time
import logging

from collect_info import CollectRSS
from set_rule import SetRule
from rename_qb import qBittorrentRename
from conf import settings
from argument_parser import parse
from log import setup_logger
from utils import json_config


def create_data_file():
    if not os.path.exists(settings.info_path):
        bangumi_info = {"rss_link": "", "bangumi_info": []}
        json_config.save(settings.info_path, bangumi_info)


if __name__ == "__main__":
    args = parse()
    if args.debug:
        from const_dev import DEV_SETTINGS

        settings.init(DEV_SETTINGS)
    else:
        settings.init()
    setup_logger()
    create_data_file()
    SetRule().rss_feed()
    while True:
        CollectRSS().run()
        SetRule().run()
        qBittorrentRename().run()
        time.sleep(settings.sleep_time)
