import logging

from module.conf import VERSION, settings
from module.update import (
    data_migration,
    first_run,
    from_30_to_31,
    start_up,
)

from .aiocore import app_core
from .status import ProgramStatus

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


class Program:
    def __init__(self):
        self.program_status = ProgramStatus()
        self.app_core = app_core

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
        if not self.program_status.database:
            first_run()
            logger.info("[Core] No db file exists, create database file.")
            return {"status": "First run detected."}
        if self.program_status.legacy_data:
            logger.info(
                "[Core] Legacy data detected, starting data migration, please wait patiently."
            )
            await data_migration()
        elif self.program_status.version_update:
            # Update database
            await from_30_to_31()
            logger.info("[Core] Database updated.")
        self.program_status.img_cache
        await self.start()

    async def start(self):
        settings.load()
        await self.app_core.initialize()
        await self.app_core.start()
        logger.info("Program running.")
        return True

    async def stop(self):
        if self.program_status.is_running:
            await self.app_core.stop()
            return True

    async def restart(self) -> bool:
        await self.stop()
        # 重置任务状态，确保重启时能重新启动任务
        self.app_core.task_manager.reset_tasks_state()
        await self.start()
        return True

    def update_database(self):
        if not self.program_status.version_update:
            return {"status": "No update found."}
        else:
            start_up()
            return {"status": "Database updated."}
