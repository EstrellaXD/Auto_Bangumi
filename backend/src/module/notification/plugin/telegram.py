from typing import Any, Dict

from module.models import Notification
from module.network import RequestContent, load_image
from module.conf import get_plugin_config

from .base_notifier import BaseNotifier


from pydantic import BaseModel, Field


class Config(BaseModel):
    chat_id: str = Field(
        default="",
        alias="chat_id",
        description="Telegram chat ID, can be a single ID or comma-separated list",
    )
    token: str = Field(
        default="",
        alias="token",
        description="Telegram bot token, can be obtained from BotFather",
    )


class Notifier(BaseNotifier):
    """Telegram 通知器"""

    def __init__(self):
        super().__init__()

    def initialize(self) -> None:
        """初始化下载器"""
        # 加载配置
        self.config: Config = get_plugin_config(Config(), "notification")
        self.chat_id:str = self.config.chat_id.strip()
        self.photo_url: str = (
            f"https://api.telegram.org/bot{self.config.token}/sendPhoto"
        )
        self.message_url: str = (
            f"https://api.telegram.org/bot{self.config.token}/sendMessage"
        )

    async def post_msg(self, notify: Notification) -> bool:
        """发送 Telegram 通知"""
        try:
            message = notify.message

            photo = notify.file
            async with RequestContent() as req:
                if photo:
                    # 发送带图片的消息
                    resp = await self._send_photo(self.chat_id, req, message, photo)
                else:
                    # 发送纯文本消息
                    resp = await self._send_text(self.chat_id, req, message)

            self.logger.debug(f"Telegram notification response: {resp.status_code}")
            resp.raise_for_status()  # 确保响应状态码为 200

        except Exception as e:
            self.logger.error(f"Telegram 通知发送失败: {e}")
            return False
        return True

    async def _send_photo(self,chat_id, req, message: str, photo) -> Any:
        """发送带图片的消息"""
        data = {
            "chat_id": chat_id,
            "caption": message,
            "disable_notification": True,
        }
        return await req.post_data(self.photo_url, data, files={"photo": photo})

    async def _send_text(self, chat_id,req, message: str) -> Any:
        """发送纯文本消息"""
        data = {
            "chat_id": chat_id,
            "text": message,
            "disable_notification": True,
        }
        return await req.post_data(self.message_url, data)
