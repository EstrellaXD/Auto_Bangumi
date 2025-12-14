from imp import new_module
import logging

from version import APP_VERSION

from .aiocore import app_core
from .status import ProgramStatus
from log import setup_logger

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
        logger.info(f"Version {APP_VERSION}  Author: EstrellaXD Twitter: https://twitter.com/Estrella_Pan")
        logger.info("GitHub: https://github.com/EstrellaXD/Auto_Bangumi/")
        logger.info("Starting AutoBangumi...")

    async def startup(self):
        self.__start_info()
        # db 进入的时候会会自动创建 data,poster 目录,以及数据库文件
        from module.database import check_and_upgrade_database,Database
        try:
            check_and_upgrade_database()
        except Exception as e:
            logger.error(f"数据库升级过程中出现异常: {e}")
            raise 
        # 确保默认用户存在
        with Database() as db:
            db.user.add_default_user()
        await self.start()

    async def start(self):
        logger.debug("[Program] loading settings...")
        # settings.load()
        # 对各个模块进行初始化, logger 在 之前已经在 api.__init__ 中设置过了
        # Program 则在config的时候初始化过
        # 初始化网络模块
        import module.network as network_module
        network_module.init()
        # 初始化解析模块
        import module.parser as parser_module
        parser_module.init()
        # 初始化下载模块
        import module.downloader as downloader_module
        downloader_module.init()
        # 初始化通知模块
        import module.notification as notifier_module
        notifier_module.init()
        # 初始化重命名模块
        import module.rename as renamer_module
        renamer_module.init()
        # 重新应用日志配置以反映设置更改
        setup_logger()
        logger.debug("[Program] log configuration applied.")
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

