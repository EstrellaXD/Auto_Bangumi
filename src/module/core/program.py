import logging

from .sub_thread import RenameThread, RSSThread
from .rss_feed import add_rss_feed

from module.conf import settings, VERSION
from module.update import data_migration

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
        if self.first_run:
            logger.info("First run detected, please configure the program in webui.")
            return {"status": "First run detected."}
        if self.legacy_data:
            logger.info(
                "Legacy data detected, starting data migration, please wait patiently."
            )
            data_migration()
        self.start()

    def start(self):
        if self.first_run:
            return {"status": "Not ready to start."}
        self.stop_event.clear()
        settings.load()
        if self.downloader_status:
            if self.enable_renamer:
                self.rename_start()
            if self.enable_rss:
                add_rss_feed()
                self.rss_start()
            logger.info("Program running.")
            return {"status": "Program started."}
        else:
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
