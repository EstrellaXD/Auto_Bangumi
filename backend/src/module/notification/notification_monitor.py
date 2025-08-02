import asyncio
import logging
from collections import defaultdict
from typing import Any

from module.conf import settings
from module.models import Notification
from module.notification import PostNotification
from module.utils.events import Event, EventBus, EventType, event_bus

logger = logging.getLogger(__name__)


class NotificationMonitor:
    """
    通知监控器 - 监听事件并发送通知
    支持集数批量通知功能
    """

    def __init__(self):
        self._event_bus: EventBus | None = event_bus
        self._notification_sender = PostNotification()
        self._running = False
        self.event_bus = event_bus

    @property
    def enabled(self) -> bool:
        """检查通知监控器是否启用"""
        return settings.notification.enable

    async def initialize(self):
        """初始化通知监控器"""
        logger.info("[NotificationMonitor] 初始化通知监控器")
        self._running = True
        self.event_bus.subscribe(
            EventType.NOTIFICATION_REQUEST,
            self.handle_notification_request,
        )

    async def shutdown(self):
        """关闭通知监控器"""
        logger.info("[NotificationMonitor] 关闭通知监控器")
        self._running = False
        self.event_bus.unsubscribe(
            EventType.NOTIFICATION_REQUEST,
            self.handle_notification_request,
        )

    async def handle_notification_request(self, event: Event) -> None:
        """处理重命名完成事件"""
        if not self._running:
            return

        try:
            data = event.data
            notify_info = data.get("notify_info", {})
            if not notify_info:
                logger.warning("[NotificationMonitor] 重命名完成事件缺少 notify_info")
                return

            # 添加到批量通知队列

            await self._notification_sender.send(notify_info)

            logger.info(
                f"[NotificationMonitor] 处理通知: {notify_info.title} - {notify_info.season} - {notify_info.episode}"
            )

        except Exception as e:
            logger.error(f"[NotificationMonitor] 处理重命名完成事件失败: {e}")

    def get_status(self) -> dict[str, Any]:
        """获取监控器状态"""
        return {
            "running": self._running,
            "enabled": self._notification_sender is not None,
        }
