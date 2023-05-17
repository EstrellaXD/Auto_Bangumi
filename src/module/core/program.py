import logging

from .sub_thread import RenameThread, RSSThread

from module.conf import settings, VERSION

logger = logging.getLogger(__name__)


class Program(RenameThread, RSSThread):
    @staticmethod
    def __start_info():
        with open("icon", "r") as f:
            for line in f.readlines():
                logger.info(line.strip("\n"))
        logger.info(
            f"Version {VERSION}  Author: EstrellaXD Twitter: https://twitter.com/Estrella_Pan"
        )
        logger.info("GitHub: https://github.com/EstrellaXD/Auto_Bangumi/")
        logger.info("Starting AutoBangumi...")

    async def startup(self):
        self.__start_info()
        await self.start()

    async def start(self):
        self.stop_event.clear()
        settings.load()
        if self.enable_renamer:
            self.rename_start()
            logger.info("Renamer started.")
        if self.enable_rss:
            self.rss_start()
            logger.info("RSS started.")
        return {"status": "Program started."}

    async def stop(self):
        if self.is_running:
            self.stop_event.set()
            self.rename_stop()
            self.rss_stop()
        else:
            return {"status": "Program is not running."}

    async def restart(self):
        await self.stop()
        await self.start()
        return {"status": "Program restarted."}
