from typing import Any

from module.models import Message
from module.network import RequestContent
from module.utils.cache_image import str_to_url

from .base_notifier import BaseNotifier


class Notifier(BaseNotifier):
    """Server酱通知器"""

    def __init__(self, **kwargs):
        super().__init__()
        self.token: str = kwargs.get("token", "")
        self.notification_url = f"https://sctapi.ftqq.com/{self.token}.send"

    def initialize(self) -> None:
        """初始化通知器"""
        pass

    def format_message(self, notify: Message) -> None:
        """格式化 Server酱 通知消息"""

        # 处理海报路径
        poster_path = notify.poster_path
        if poster_path and "/" in poster_path:
            poster_path = str_to_url(poster_path.split("/")[-1])

        # Server酱 需要在消息中包含图片URL
        message = notify.message
        if poster_path:
            message += f"\n{poster_path}\n".strip()
        notify.message = message

    async def post_msg(self, notify: Message) -> bool:
        """发送 Server酱 通知"""
        try:
            self.format_message(notify)

            data = {
                "title": notify.title,
                "desp": notify.message,
            }

            async with RequestContent() as req:
                resp = await req.post_data(self.notification_url, data)

            self.logger.debug(f"ServerChan notification response: {resp.status_code}")
            return resp and resp.status_code == 200

        except Exception as e:
            self.logger.error(f"Server酱 通知发送失败: {e}")
            return False
