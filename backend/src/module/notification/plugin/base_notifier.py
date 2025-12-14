import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from models import Message

logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    """
    通知器基类，定义统一的通知接口
    """

    def __init__(self):
        self.chat_id: str = ""
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def post_msg(self, notify: Message) -> bool:
        """
        发送通知消息

        Args:
            notify: 通知对象

        Returns:
            bool: 发送是否成功
        """
        pass

    async def send_with_retry(self, notify: Message, max_retries: int = 3) -> bool:
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
                self.logger.warning(f"通知发送失败，尝试次数: {attempt + 1}/{max_retries}")
            except Exception as e:
                self.logger.error(f"通知发送异常，尝试次数: {attempt + 1}/{max_retries} - {e}")

            if attempt < max_retries - 1:
                import asyncio

                await asyncio.sleep(2**attempt)  # 指数退避

        return False


# 保持向后兼容
Notifier = BaseNotifier
