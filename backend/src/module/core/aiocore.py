import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from .events import EventBus
from .service_registry import service_registry
from .task_manager import TaskManager

logger = logging.getLogger(__name__)


class AsyncApplicationCore:
    """异步应用核心

    负责管理所有服务和任务的生命周期
    """

    def __init__(self):
        self.task_manager = TaskManager()
        self.event_bus = EventBus()
        self.services = []
        self._download_monitor = None
        self._running: bool = False
        self._initialized: bool = False

    async def initialize(self) -> None:
        """初始化应用核心"""
        if self._initialized:
            logger.warning("[AsyncCore] 已经初始化过，跳过")
            return

        logger.info("[AsyncCore] 开始初始化...")

        try:
            # 确保服务已注册（导入服务模块）
            from .services import RSSService, DownloadService

            # 从服务注册表获取服务实例
            self.services = service_registry.create_service_instances()

            # 初始化所有服务
            for service in self.services:
                await service.initialize()
                logger.debug(f"[AsyncCore] 服务 {service.name} 初始化完成")
            ## download服务需要特殊处理,要注入event_bus
            download_service = service_registry.get_service_instance("download")
            if download_service:
                download_service.set_event_bus(self.event_bus)
                logger.debug("[AsyncCore] 已为下载服务注入事件总线")

            # 注册任务到任务管理器
            await self._register_tasks()

            # 注册事件处理器
            await self._register_event_handlers()

            self._initialized = True
            logger.info("[AsyncCore] 初始化完成")

        except Exception as e:
            logger.error(f"[AsyncCore] 初始化失败: {e}")
            await self._cleanup_services()
            raise

    async def _register_tasks(self) -> None:
        """注册任务"""
        for service in self.services:
            config = service.get_task_config()
            if config["enabled"]:
                await self.task_manager.register_task(
                    name=config["name"],
                    coro_func=service.execute,
                    interval=config["interval"],
                    max_retries=config["max_retries"],
                )
                logger.debug(f"[AsyncCore] 注册任务: {config['name']}")

    async def _register_event_handlers(self) -> None:
        """注册事件处理器"""
        try:
            from module.downloader.download_monitor import DownloadMonitor
            from module.core.events import EventType

            # 创建并注册 DownloadMonitor，注入 event_bus
            self._download_monitor = DownloadMonitor(event_bus=self.event_bus)
            self.event_bus.subscribe(
                EventType.DOWNLOAD_STARTED,
                self._download_monitor.handle_download_started,
            )
            logger.info("[AsyncCore] 已注册 DownloadMonitor 事件处理器")

            # 为下载服务设置监控器和事件总线
            for service in self.services:
                if service.name == "download" and hasattr(
                    service, "_download_controller"
                ):
                    service._download_controller.set_download_monitor(
                        self._download_monitor
                    )
                    service._download_controller.set_event_bus(self.event_bus)
                    logger.debug("[AsyncCore] 已为下载服务设置监控器和事件总线")

        except Exception as e:
            logger.error(f"[AsyncCore] 注册事件处理器失败: {e}")
            raise

    async def start(self) -> None:
        """启动应用核心"""
        if self._running:
            logger.warning("[AsyncCore] 应用已在运行")
            return

        if not self._initialized:
            raise RuntimeError("必须先初始化应用核心")

        try:
            self._running = True
            logger.info("[AsyncCore] 启动应用...")

            await self.task_manager.start_all()
            logger.info("[AsyncCore] 所有任务已启动")

        except Exception as e:
            logger.error(f"[AsyncCore] 启动失败: {e}")
            self._running = False
            raise

    async def stop(self) -> None:
        """停止应用核心"""
        if not self._running:
            return

        logger.info("[AsyncCore] 开始停止应用...")
        self._running = False

        try:
            # 关闭任务管理器
            await self.task_manager.shutdown()
        except Exception as e:
            logger.error(f"[AsyncCore] 任务管理器关闭失败: {e}")

        # 关闭下载监控器
        try:
            if hasattr(self, "_download_monitor") and self._download_monitor:
                await self._download_monitor.shutdown()
                logger.debug("[AsyncCore] 下载监控器已关闭")
        except Exception as e:
            logger.error(f"[AsyncCore] 下载监控器关闭失败: {e}")

        # 清理服务资源
        await self._cleanup_services()

        logger.info("[AsyncCore] 应用已停止")

    async def _cleanup_services(self) -> None:
        """清理所有服务资源"""
        # 清理服务
        for service in self.services:
            try:
                await service.cleanup()
                logger.debug(f"[AsyncCore] 服务 {service.name} 清理完成")
            except Exception as e:
                logger.error(f"[AsyncCore] 服务 {service.name} 清理失败: {e}")

    def get_status(self) -> dict[str, Any]:
        """获取应用状态"""
        status = {
            "running": self._running,
            "initialized": self._initialized,
            "tasks": self.task_manager.get_status(),
            "services": [
                {"name": s.name, "initialized": getattr(s, "_initialized", False)}
                for s in self.services
            ],
            "event_bus": self.event_bus.get_subscribers_count(),
        }

        # 添加下载监控器状态
        if self._download_monitor:
            status["download_monitor"] = self._download_monitor.get_monitoring_status()

        return status

    @asynccontextmanager
    async def lifespan(self):
        """生命周期管理器"""
        try:
            await self.initialize()
            await self.start()
            yield self
        except Exception as e:
            logger.error(f"[AsyncCore] 生命周期管理器错误: {e}")
            raise
        finally:
            await self.stop()


# 全局实例
app_core = AsyncApplicationCore()


if __name__ == "__main__":

    async def main():
        async with app_core.lifespan():
            logger.info("[AsyncCore] 应用已启动，按 Ctrl+C 停止")
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("[AsyncCore] 收到停止信号")

    from module.conf import setup_logger

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    setup_logger()
    asyncio.run(main())
