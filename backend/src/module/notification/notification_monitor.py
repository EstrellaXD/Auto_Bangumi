import logging

from module.utils.events import Event, EventType, EventBus
from module.models import Bangumi, Torrent, Notification
from module.notification import PostNotification

logger = logging.getLogger(__name__)


class NotificationMonitor:
    """通知监控器
    
    监听重命名完成事件，触发通知发送
    """

    def __init__(self, event_bus: EventBus | None = None):
        self._event_bus: EventBus | None = event_bus
        self._notification: PostNotification | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """初始化通知器"""
        if not self._initialized:
            self._notification = PostNotification()
            self._initialized = True
            logger.info("[NotificationMonitor] 初始化完成")

    async def handle_rename_completed(self, event: Event) -> None:
        """处理重命名完成事件
        
        Args:
            event: 重命名完成事件，包含torrent和bangumi信息
        """
        if not self._initialized or not self._notification:
            logger.error("[NotificationMonitor] 服务未初始化")
            return

        torrent = event.data.get("torrent")
        bangumi = event.data.get("bangumi")

        if not torrent or not bangumi:
            logger.warning("[NotificationMonitor] 事件数据不完整")
            return

        try:
            logger.info(f"[NotificationMonitor] 准备发送通知: {torrent.name}")
            
            # 创建通知数据
            notify_info = Notification(
                title=bangumi.official_title,
                season=bangumi.season,
                episode="重命名完成",
                poster_path=bangumi.poster_link,
            )
            
            # 发送通知
            await self._notification.send(notify_info)
            logger.info(f"[NotificationMonitor] 通知已发送: {bangumi.official_title}")
            
        except Exception as e:
            logger.error(f"[NotificationMonitor] 发送通知失败: {torrent.name} - {e}")

    async def shutdown(self) -> None:
        """关闭通知监控器"""
        logger.info("[NotificationMonitor] 通知监控器已关闭")