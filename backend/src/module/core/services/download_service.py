
import logging
from typing import TYPE_CHECKING, Any
from typing_extensions import override

from module.downloader.download_queue import DownloadController
from module.utils.events import ServiceException
from .base_services import BaseService

logger = logging.getLogger(__name__)


class DownloadService(BaseService):
    def __init__(self):
        super().__init__()
        self._download_controller:DownloadController|None = None

    async def _setup(self) -> None:
        # 预检查下载模块是否可用
        try:
            from module.downloader import Client, DownloadController

            # 初始化下载客户端
            logger.debug("[DownloadService] start initialize")
            Client.initialize()
            Client.start()
            logger.debug("[DownloadService] 下载客户端已启动")

            self._download_controller = DownloadController()

        except ImportError as e:
            logger.error(f"[DownloadService] 下载模块导入失败: {e}")
            raise

    def get_task_config(self) -> dict[str, Any]:
        """获取下载任务配置"""
        return {
            "name": "download_process",
            "interval": 10,
            "enabled": True,
        }

    @override
    async def execute(self) -> None:
        """执行下载任务"""
        try:
            if not self._download_controller:
                raise ServiceException("download", "下载控制器未初始化")

            await self._download_controller.download()
            logger.debug("[DownloadService] 下载任务完成")
        except TimeoutError:
            logger.error("[DownloadService] 无法连接到下载器")
            raise
        except Exception as e:
            logger.error(f"[DownloadService] 执行失败: {e}")
            raise ServiceException("download", f"执行失败: {e}")

    async def cleanup(self) -> None:
        """清理下载客户端"""
        try:
            from module.downloader import Client

            await Client.stop()
            self._initialized:bool = False
            logger.debug("[DownloadService] 下载客户端已重启")
        except Exception as e:
            logger.error(f"[DownloadService] 清理失败: {e}")
            raise ServiceException("download", f"清理失败: {e}")
