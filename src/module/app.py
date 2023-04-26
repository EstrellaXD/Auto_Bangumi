import os
import time
import logging

from module.conf import settings, setup_logger, LOG_PATH, DATA_PATH, RSSLink, VERSION
from module.utils import load_program_data, save_program_data

from module.core import DownloadClient
from module.manager import Renamer, FullSeasonGet
from module.rss import RSSAnalyser
from module.models import ProgramData


logger = logging.getLogger(__name__)


def reset_log():
    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)


def load_data_file(rss_link: str) -> ProgramData:
    empty_data = ProgramData(
        rss_link=rss_link,
        data_version=settings.data_version,
    )
    if not os.path.exists(DATA_PATH):
        program_data = empty_data
        save_program_data(DATA_PATH, program_data)
        logger.info("Building data information...")
    else:
        program_data = load_program_data(DATA_PATH)
        if program_data.rss_link != rss_link or program_data.data_version != settings.data_version:
            program_data = empty_data
            logger.info("Rebuilding data information...")
    return program_data


def main_process(program_data: ProgramData, download_client: DownloadClient):
    rename = Renamer(download_client)
    rss_analyser = RSSAnalyser()
    while True:
        times = 0
        if settings.rss_parser.enable:
            rss_analyser.run(program_data.bangumi_info, download_client, program_data.rss_link)
        if settings.bangumi_manage.eps_complete and program_data.bangumi_info != []:
            FullSeasonGet().eps_complete(program_data.bangumi_info, download_client)
        logger.info("Running....")
        save_program_data(DATA_PATH, program_data)
        while times < settings.program.rename_times:
            if settings.bangumi_manage.enable:
                rename.rename()
            times += 1
            time.sleep(settings.program.sleep_time / settings.program.rename_times)


def show_info():
    with open("icon", "r") as f:
        for line in f.readlines():
            logger.info(line.strip("\n"))
    logger.info(f"Version {VERSION}  Author: EstrellaXD Twitter: https://twitter.com/Estrella_Pan")
    logger.info("GitHub: https://github.com/EstrellaXD/Auto_Bangumi/")
    logger.info("Starting AutoBangumi...")


def run():
    # 初始化
    settings.reload()
    rss_link = RSSLink()
    reset_log()
    setup_logger()
    show_info()
    if settings.rss_parser.token in ["", "token", None]:
        logger.error("Please set your RSS token in config file.")
        exit(1)
    download_client = DownloadClient()
    download_client.auth()
    download_client.init_downloader()
    download_client.rss_feed(rss_link)
    bangumi_data = load_data_file(rss_link)
    # 主程序循环
    main_process(bangumi_data, download_client)
