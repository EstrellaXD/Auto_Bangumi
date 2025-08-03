import logging

from module.conf import VERSION, settings

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
            from module.update import first_run

            first_run()
            logger.info("[Core] No db file exists, create database file.")

        from module.database import check_and_upgrade_database

        if not check_and_upgrade_database():
            logger.error("数据库升级失败，程序无法启动")
            raise RuntimeError("数据库升级失败")

        # 检查是否需要创建图片缓存目录
        self.program_status.img_cache
        await self.start()

    async def start(self):
        logger.debug("[Program] loading settings...")
        settings.load()
        logger.debug("[Program] settings loaded.")
        logger.debug("[Program] starting application core...")
        await self.app_core.initialize()
        await self.app_core.start()
        logger.debug("[Program] application core started.")
        logger.info("Program running.")
        return True

    async def stop(self):
        if self.program_status.is_running:
            logger.info("[Program] stopping application core...")
            await self.app_core.stop()
            logger.info("[Program] application core stopped.")
            return True

    async def restart(self) -> bool:
        logger.info("[Program] waiting for application  stop...")
        await self.stop()
        logger.info("[Program] application stopped, starting again...")
        # 重置任务状态，确保重启时能重新启动任务
        self.app_core.task_manager.reset_tasks_state()
        await self.start()
        return True

    def update_database(self):
        if not self.program_status.version_update:
            return {"status": "No update found."}
        else:
            from module.update import start_up

            start_up()
            return {"status": "Database updated."}
