from __future__ import annotations

import logging
from enum import Enum

from module.conf import settings
from module.database import Database
from module.models import Notification
from module.network import load_image
import importlib

from module.notification.plugin.log import Notifier

logger = logging.getLogger(__name__)


NOTIFICATON_TYPE = ["tetegram", "bark", "server_chan", "wecom", "log"]


class NotificationProcessor:
    """
    通知处理器 - 负责通知数据的解析和格式化
    分离了数据处理逻辑，不直接负责发送
    """

    @staticmethod
    def get_poster_from_db(title: str) -> str:
        """
        从数据库获取番剧海报
        """
        try:
            with Database() as db:
                bangumi = db.bangumi.search_official_title(title)
            return bangumi.poster_link if bangumi and bangumi.poster_link else ""
        except Exception as e:
            logger.error(f"获取海报失败: {title} - {e}")
            return ""

    async def process_notification(self, notify: Notification) -> Notification:
        """
        处理通知对象，进行必要的数据解析和补充
        """
        # 创建副本，避免修改原对象
        processed = Notification(
            title=notify.title,
            season=notify.season,
            episode=notify.episode,
            poster_path=notify.poster_path,
            message=notify.message,
        )
        # 想了想,对每个通知直接传file和post_link, 这样就可以直接用来发送了
        # 生成默认消息
        if processed.episode:
            processed.message = f"番剧名称：{processed.title}\n季度：第{processed.season}季\n更新集数：第{processed.episode}集"
            # 获取海报
            if not processed.poster_path and processed.title:
                logger.debug(f"[NotificationProcessor] 获取海报: {processed.title}")
                processed.poster_path = self.get_poster_from_db(processed.title)

        processed.file = (
            await load_image(processed.poster_path) if processed.poster_path else None
        )

        return processed


class PostNotification:
    """
    使用新的 NotificationManager 进行管理
    """

    def __init__(self) -> None:
        self.processor = NotificationProcessor()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.notifier = None

    def initialize(self) -> None:
        """根据设置创建通知管理器"""
        self.notifier = self._get_notifier()
        self.notifier.initialize()

    def _get_notifier(self):
        notification_type = settings.notification.type
        package_path = f"module.notification.plugin.{notification_type}"
        try:
            notification_module = importlib.import_module(package_path)
        except ImportError as e:
            logger.error(f"加载通知器失败: {notification_type} - {e}")
            notification_module = importlib.import_module(
                "module.notification.plugin.log"
            )
            logger.warning(
                f"使用默认日志通知器: {notification_module.Notifier.__name__}"
            )
        Notifier = notification_module.Notifier
        logger.debug(f"加载通知器: {Notifier.__name__}")
        return Notifier()

    async def send(self, notify: Notification) -> bool:
        """
        发送通知

        Args:
            notify: 通知对象

        Returns:
            bool: 是否发送成功（至少一个通知器成功）
        """
        # 处理通知数据
        processed_notify = await self.processor.process_notification(notify)

        # 发送通知
        result = await self.notifier.post_msg(processed_notify)

        return result


if __name__ == "__main__":
    import asyncio

    from module.conf import setup_logger

    setup_logger("DEBUG", reset=True)

    # 测试用例
    title = "败犬"
    link = "posters/aHR0cHM6Ly9pbWFnZS50bWRiLm9yZy90L3Avdzc4MC9wYWRSbWJrMkxkTGd1ZGg1Y0xZMG85VEZ6aEkuanBn"
    nt = Notification(title=title, season=1, episode="1", poster_path=link)
    sender = PostNotification()
    sender.initialize()

    async def test():
        success = await sender.send(nt)
        print(f"发送结果: {success}")

    asyncio.run(test())
