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
        self.name: str = name
        self._initialized: bool = False

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
