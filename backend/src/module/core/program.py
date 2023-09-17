import logging

from module.conf import VERSION, settings
from module.update import data_migration, from_30_to_31, start_up, first_run

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
            return {"status": "Program started."}
        else:
            self.stop_event.set()
            return {"status": "Can't connect to downloader. Program not paused."}

    def stop(self):
        if self.is_running:
            self.stop_event.set()
            self.rename_stop()
            self.rss_stop()
            return {"status": "Program stopped."}
        else:
            return {"status": "Program is not running."}

    def restart(self):
        self.stop()
        self.start()
        return {"status": "Program restarted."}

    def update_database(self):
        if not self.version_update:
            return {"status": "No update found."}
        else:
            start_up()
            return {"status": "Database updated."}
