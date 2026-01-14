import logging
import asyncio

from module.conf import VERSION, settings
from module.models import ResponseModel
from module.update import (
    data_migration,
    first_run,
    from_30_to_31,
    start_up,
    cache_image,
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
    def __init__(self):
        super().__init__()
        self._start_task = None

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
            from_30_to_31()
            logger.info("[Core] Database updated.")
        if not self.img_cache:
            logger.info("[Core] No image cache exists, create image cache.")
            cache_image()
        await self.start()

    async def start(self):
        self.stop_event.clear()
        settings.load()
        if self._start_task and not self._start_task.done():
            self._start_task.cancel()
        self._start_task = asyncio.create_task(self.start_service())
        logger.info("Program running.")
        return ResponseModel(
            status=True,
            status_code=200,
            msg_en="Program started.",
            msg_zh="程序启动成功。",
        )

    async def start_service(self):
        try:
            retry_count = 0
            # max_retries = settings.program.max_retries if hasattr(settings, "program") and hasattr(settings.program, "max_retries") else 5
            max_retries = 5
            while not self.downloader_status:
                if self.stop_event.is_set():
                    return
                retry_count += 1
                if retry_count > max_retries:
                    logger.error("Downloader connection failed after maximum retries.")
                    return
                logger.warning(f"Downloader is not running. Retry {retry_count}/{max_retries}")
                logger.info("Waiting for downloader to start.")
                await asyncio.sleep(30)
            
            if self.stop_event.is_set():
                return

            if self.enable_renamer and not self.rename_thread.is_alive():
                self.rename_start()
            if self.enable_rss and not self.rss_thread.is_alive():
                self.rss_start()
        except asyncio.CancelledError:
            logger.debug("Start service task cancelled.")
        except Exception as e:
            logger.error(f"Error in start service: {e}", exc_info=True)

    def stop(self):
        if self.is_running:
            self.stop_event.set()
            if self._start_task and not self._start_task.done():
                self._start_task.cancel()
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

    async def restart(self):
        self.stop()
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
