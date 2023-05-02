import os
import time
import logging

from module.conf import setup_logger, LOG_PATH, DATA_PATH, RSSLink, VERSION
from module.utils import load_program_data, save_program_data

from module.core import DownloadClient
from module.manager import Renamer, FullSeasonGet
from module.rss import RSSAnalyser
from module.models import ProgramData, Config


logger = logging.getLogger(__name__)


def reset_log():
    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)


def load_data_file(rss_link: str, data_version) -> ProgramData:
    empty_data = ProgramData(
        rss_link=rss_link,
        data_version=data_version,
    )
    if not os.path.exists(DATA_PATH):
        program_data = empty_data
        save_program_data(DATA_PATH, program_data)
        logger.info("Building data information...")
    else:
        program_data = load_program_data(DATA_PATH)
        if program_data.rss_link != rss_link or program_data.data_version != data_version:
            program_data = empty_data
            logger.info("Rebuilding data information...")
    return program_data


def main_process(program_data: ProgramData, download_client: DownloadClient, _settings: Config):
    rename = Renamer(download_client, _settings)
    rss_analyser = RSSAnalyser(_settings)
    while True:
        times = 0
        if _settings.rss_parser.enable:
            rss_analyser.run(program_data.bangumi_info, program_data.rss_link)
            download_client.add_rules(program_data.bangumi_info, program_data.rss_link)
        if _settings.bangumi_manage.eps_complete and program_data.bangumi_info != []:
            FullSeasonGet(settings=_settings).eps_complete(program_data.bangumi_info, download_client)
        logger.info("Running....")
        save_program_data(DATA_PATH, program_data)
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
    bangumi_data = load_data_file(rss_link, settings.data_version)
    # 主程序循环
    main_process(bangumi_data, download_client, settings)
