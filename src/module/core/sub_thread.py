import os.path
import time
import logging
import threading

from .data_migration import data_migration
from .check import check_status

from module.rss import RSSAnalyser, add_rules
from module.manager import Renamer, FullSeasonGet
from module.database import BangumiDatabase
from module.downloader import DownloadClient
from module.conf import settings, VERSION, DATA_PATH

logger = logging.getLogger(__name__)

stop_event = threading.Event()


def rss_loop(stop_event):
    rss_analyser = RSSAnalyser()
    rss_link = settings.rss_link()
    while not stop_event.is_set():
        rss_analyser.run(rss_link)
        add_rules()
        if settings.bangumi_manage.eps_complete:
            with FullSeasonGet() as full_season_get:
                full_season_get.eps_complete()
        stop_event.wait(settings.program.rss_time)


def rename_loop(stop_event):
    while not stop_event.is_set():
        with Renamer() as renamer:
            renamer.rename()
        stop_event.wait(settings.program.rename_time)


rss_thread = threading.Thread(
    target=rss_loop,
    args=(stop_event,),
)

rename_thread = threading.Thread(
    target=rename_loop,
    args=(stop_event,),
)


def start_info():
    with open("icon", "r") as f:
        for line in f.readlines():
            logger.info(line.strip("\n"))
    logger.info(
        f"Version {VERSION}  Author: EstrellaXD Twitter: https://twitter.com/Estrella_Pan"
    )
    logger.info("GitHub: https://github.com/EstrellaXD/Auto_Bangumi/")
    logger.info("Starting AutoBangumi...")


def stop_thread():
    global rss_thread, rename_thread
    if not stop_event.is_set():
        stop_event.set()
        rename_thread.join()
        rss_thread.join()


def start_thread():
    global rss_thread, rename_thread
    if not check_status():
        stop_event.set()
        return {"status": "start failed"}
    if stop_event.is_set():
        stop_event.clear()
        time.sleep(1)
        settings.load()
        rss_thread = threading.Thread(target=rss_loop, args=(stop_event,))
        rename_thread = threading.Thread(target=rename_loop, args=(stop_event,))
        if settings.rss_parser.enable:
            rss_thread.start()
        if settings.bangumi_manage.enable:
            rename_thread.start()
        return {"status": "ok"}


def first_run():
    if not os.path.exists(DATA_PATH):
        if data_migration():
            logger.info("Updated, data migration completed.")
        else:
            logger.info("First run, init downloader.")
            with DownloadClient() as client:
                client.init_downloader()
                client.add_rss_feed(settings.rss_link())


async def start_program():
    global rss_thread, rename_thread
    start_info()
    if not check_status():
        stop_event.set()
        logger.info("Program paused.")
    else:
        first_run()
        with BangumiDatabase() as database:
            database.update_table()
        rss_thread = threading.Thread(target=rss_loop, args=(stop_event,))
        rename_thread = threading.Thread(target=rename_loop, args=(stop_event,))
        if settings.rss_parser.enable:
            rss_thread.start()
        if settings.bangumi_manage.enable:
            rename_thread.start()


