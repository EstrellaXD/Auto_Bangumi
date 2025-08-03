import asyncio
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from typing_extensions import override

from module.conf import settings
from module.utils.events import ServiceException

if TYPE_CHECKING:
    from module.rss import RSSEngine

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """服务基类"""

    def __init__(self, name: str | None = None):
        # 如果没有指定名称，使用类名自动生成
        if name is None:
            name = self.__class__.__name__.lower().replace("service", "")
        self.name = name
        self._initialized = False

    async def initialize(self) -> None:
        """初始化服务"""
        if not self._initialized:
            try:
                await self._setup()
                self._initialized = True
                logger.info(f"[{self.name}Service] 初始化完成")
            except Exception as e:
                logger.error(f"[{self.name}Service] 初始化失败: {e}")
                raise ServiceException(self.name, f"初始化失败: {e}")

    @abstractmethod
    async def _setup(self) -> None:
        """子类实现具体初始化逻辑"""
        pass

    @abstractmethod
    async def execute(self) -> None:
        """执行服务逻辑"""
        pass

    @abstractmethod
    def get_task_config(self) -> dict[str, Any]:
        """获取任务配置"""
        pass

    async def cleanup(self) -> None:
        """清理资源"""
        pass

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized


class RSSService(BaseService):
    def __init__(self):
        super().__init__()
        self._engine: RSSEngine | None = None
        self._eps_complete_enabled: bool = False

    async def _setup(self) -> None:
        from module.rss import RSSEngine

        self._engine = RSSEngine()
        self._eps_complete_enabled = settings.bangumi_manage.eps_complete

    def get_task_config(self) -> dict[str, Any]:
        """获取RSS任务配置"""

        return {
            "name": "rss_refresh",
            "interval": settings.program.rss_time,
            "enabled": True,
        }

    async def execute(self) -> None:
        """执行RSS刷新任务"""
        if not self._engine:
            raise ServiceException("rss", "服务未初始化")

        try:
            await self._engine.refresh_all()

            if self._eps_complete_enabled:
                from module.downloader import DownloadQueue
                from module.manager import eps_complete

                # 要等到 download queue 空了后再做这个,不然会重复下载
                # 等太久了就说明现在挺重的, 就先不 eps 了
                await asyncio.wait_for(DownloadQueue().queue.join(), timeout=60)
                await eps_complete()

            logger.debug("[RSSService] RSS刷新完成")
        except Exception as e:
            logger.error(f"[RSSService] 执行失败: {e}")
            raise ServiceException("rss", f"执行失败: {e}")


class DownloadService(BaseService):
    def __init__(self):
        super().__init__()
        self._download_controller = None

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
            "max_retries": 5,
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
            self._initialized = False
            logger.debug("[DownloadService] 下载客户端已重启")
        except Exception as e:
            logger.error(f"[DownloadService] 清理失败: {e}")
            raise ServiceException("download", f"清理失败: {e}")
