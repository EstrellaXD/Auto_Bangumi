import asyncio
import logging

from module.conf import VERSION, settings
from module.models import ResponseModel
from module.update import (
    cache_image,
    data_migration,
    first_run,
    from_30_to_31,
    start_up,
)

from .sub_thread import RenameThread, RSSThread

logger = logging.getLogger(__name__)

figlet = r"""
               _        ____                                    _
    /\        | |      |  _ \                                  (_)
   /  \  _   _| |_ ___ | |_) | __ _ _ __   __ _ _   _ _ __ ___  _
  / /\ \| | | | __/ _ \|  _ < / _` | '_ \ / _` | | | | '_ ` _ \| |
 / ____ \ |_| | || (_) | |_) | (_| | | | | (_| | |_| | | | | | | |
/_/    \_\__,_|\__\___/|____/ \__,_|_| |_|\__, |\__,_|_| |_| |_|_|
                                           __/ |
                                          |___/
"""


class Program(RenameThread, RSSThread):
    @staticmethod
    def __start_info():
        for line in figlet.splitlines():
            logger.info(line.strip("\n"))
        logger.info(
            f"Version {VERSION}  Author: EstrellaXD Twitter: https://twitter.com/Estrella_Pan"
        )
        logger.info("GitHub: https://github.com/EstrellaXD/Auto_Bangumi/")
        logger.info("Starting AutoBangumi...")

    async def startup(self):
        self.__start_info()
        if not self.database:
            first_run()
            logger.info("[Core] No db file exists, create database file.")
            return {"status": "First run detected."}
        if self.legacy_data:
            logger.info(
                "[Core] Legacy data detected, starting data migration, please wait patiently."
            )
            data_migration()
        elif self.version_update:
            # Update database
            await from_30_to_31()
            logger.info("[Core] Database updated.")
        if not self.img_cache:
            logger.info("[Core] No image cache exists, create image cache.")
            await cache_image()
        await self.start()

    async def start(self):
        self.stop_event.clear()
        settings.load()
        while not await self.check_downloader_status():
            logger.warning("Downloader is not running.")
            logger.info("Waiting for downloader to start.")
            await asyncio.sleep(30)
        if self.enable_renamer:
            self.rename_start()
        if self.enable_rss:
            self.rss_start()
        logger.info("Program running.")
        return ResponseModel(
            status=True,
            status_code=200,
            msg_en="Program started.",
            msg_zh="程序启动成功。",
        )

    async def stop(self):
        if self.is_running:
            self.stop_event.set()
            await self.rename_stop()
            await self.rss_stop()
            return ResponseModel(
                status=True,
                status_code=200,
                msg_en="Program stopped.",
                msg_zh="程序停止成功。",
            )
        else:
            return ResponseModel(
                status=False,
                status_code=406,
                msg_en="Program is not running.",
                msg_zh="程序未运行。",
            )

    async def restart(self):
        await self.stop()
        await self.start()
        return ResponseModel(
            status=True,
            status_code=200,
            msg_en="Program restarted.",
            msg_zh="程序重启成功。",
        )

    def update_database(self):
        if not self.version_update:
            return {"status": "No update found."}
        else:
            start_up()
            return {"status": "Database updated."}
