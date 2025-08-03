from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from module.conf import settings
from module.database import Database
from module.models import Notification
from module.network import load_image
from module.notification.manager import (
    NotificationConfig,
    NotificationManager,
    NotificationType,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


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
    现代化的通知发送类
    使用新的 NotificationManager 进行管理
    保持向后兼容的接口
    """

    def __init__(self) -> None:
        self.processor = NotificationProcessor()
        self.manager = self._create_manager_from_settings()
        self.logger = logging.getLogger(self.__class__.__name__)

    def _create_manager_from_settings(self) -> NotificationManager:
        """根据设置创建通知管理器"""
        configs = []

        if settings.notification.enable:
            # 解析多个chat_id
            chat_ids = [
                cid.strip()
                for cid in settings.notification.chat_id.split(",")
                if cid.strip()
            ]

            # 确定通知类型
            try:
                notification_type = NotificationType(settings.notification.type)
            except ValueError:
                logger.warning(
                    f"未知的通知类型: {settings.notification.type}，回退到log"
                )
                notification_type = NotificationType.LOG

            # 为每个chat_id创建配置
            if chat_ids and notification_type in [
                NotificationType.TELEGRAM,
                NotificationType.WECOM,
            ]:
                for chat_id in chat_ids:
                    config = NotificationConfig(
                        type=notification_type,
                        token=settings.notification.token,
                        chat_id=chat_id,
                        enabled=True,
                    )
                    configs.append(config)
            else:
                # 单个配置
                config = NotificationConfig(
                    type=notification_type,
                    token=settings.notification.token,
                    enabled=True,
                )
                configs.append(config)
        else:
            # 禁用时使用日志通知
            config = NotificationConfig(
                type=NotificationType.LOG, token="", enabled=True
            )
            configs.append(config)

        return NotificationManager(configs)

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
        results = await self.manager.send_notification(processed_notify)

        # 只要有一个成功就返回True（保持向后兼容）
        return any(results.values()) if results else False

    def get_status(self) -> dict:
        """获取通知系统状态"""
        return self.manager.get_status()


# 为了向后兼容，保留旧的类名
NotificationSender = PostNotification


if __name__ == "__main__":
    import asyncio

    from module.conf import setup_logger

    setup_logger("DEBUG", reset=True)

    # 测试用例
    title = "败犬"
    link = "posters/aHR0cHM6Ly9pbWFnZS50bWRiLm9yZy90L3Avdzc4MC9wYWRSbWJrMkxkTGd1ZGg1Y0xZMG85VEZ6aEkuanBn"
    nt = Notification(title=title, season=1, episode="1", poster_path=link)

    async def test():
        sender = PostNotification()
        success = await sender.send(nt)
        print(f"发送结果: {success}")
        print(f"系统状态: {sender.get_status()}")

    asyncio.run(test())
