import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from module.models import Notification

logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    """
    通知器基类，定义统一的通知接口
    """

    def __init__(self, token: str, **kwargs):
        self.token = token
        self.config = kwargs
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def post_msg(self, notify: Notification) -> bool:
        """
        发送通知消息

        Args:
            notify: 通知对象

        Returns:
            bool: 发送是否成功
        """
        pass

    def format_message(self, notify: Notification) -> Dict[str, Any]:
        """
        格式化通知消息，子类可重写此方法

        Args:
            notify: 通知对象

        Returns:
            Dict[str, Any]: 格式化后的消息数据
        """
        message = notify.message
        if not message and notify.episode:
            message = f"番剧名称：{notify.title}\n季度：第{notify.season}季\n更新集数：第{notify.episode}集"

        return {
            "title": notify.title,
            "message": message,
            "poster_path": notify.poster_path,
            "season": notify.season,
            "episode": notify.episode,
        }

    async def send_with_retry(self, notify: Notification, max_retries: int = 3) -> bool:
        """
        带重试机制的发送

        Args:
            notify: 通知对象
            max_retries: 最大重试次数

        Returns:
            bool: 发送是否成功
        """
        for attempt in range(max_retries):
            try:
                result = await self.post_msg(notify)
                if result:
                    return True
                self.logger.warning(
                    f"通知发送失败，尝试次数: {attempt + 1}/{max_retries}"
                )
            except Exception as e:
                self.logger.error(
                    f"通知发送异常，尝试次数: {attempt + 1}/{max_retries} - {e}"
                )

            if attempt < max_retries - 1:
                import asyncio

                await asyncio.sleep(2**attempt)  # 指数退避

        return False


# 保持向后兼容
Notifier = BaseNotifier
