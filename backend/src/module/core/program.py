import logging

from module.conf import VERSION, settings
from module.models import ResponseModel
from module.update import (
    data_migration,
    first_run,
    from_30_to_31,
    start_up,
    cache_image,
    torrent_migration,
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

    def startup(self):
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
            from_30_to_31()
            logger.info("[Core] Database updated.")
        if not self.img_cache:
            logger.info("[Core] No image cache exists, create image cache.")
            cache_image()
        if not self.torrent_hash:
            logger.info(
                "[Core] The hash field of the torrent table does not exist or its value is empty, get torrent hash."
            )
            torrent_migration()
        self.start()

    def start(self):
        self.stop_event.clear()
        settings.load()
        if self.downloader_status:
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
        else:
            self.stop_event.set()
            logger.warning("Program failed to start.")
            return ResponseModel(
                status=False,
                status_code=406,
                msg_en="Program failed to start.",
                msg_zh="程序启动失败。",
            )

    def stop(self):
        if self.is_running:
            self.stop_event.set()
            self.rename_stop()
            self.rss_stop()
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

    def restart(self):
        self.stop()
        self.start()
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
