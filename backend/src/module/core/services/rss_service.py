from typing import TYPE_CHECKING, Any
import asyncio
import logging

from module.conf import settings
from module.rss import RSSEngine
from module.utils.events import ServiceException

from .base_services import BaseService

if TYPE_CHECKING:
    from module.rss import RSSEngine
logger = logging.getLogger(__name__)


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
