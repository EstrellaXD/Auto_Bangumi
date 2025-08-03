from typing import Any, Dict

from module.models import Notification
from module.network import RequestContent, load_image

from .base_notifier import BaseNotifier


class Notifier(BaseNotifier):
    """Telegram 通知器"""

    def __init__(self, token: str, chat_id: str, **kwargs):
        super().__init__(token, **kwargs)
        self.chat_id: str = chat_id
        self.photo_url: str = f"https://api.telegram.org/bot{token}/sendPhoto"
        self.message_url: str = f"https://api.telegram.org/bot{token}/sendMessage"

    async def post_msg(self, notify: Notification) -> bool:
        """发送 Telegram 通知"""
        try:
            message = notify.message

            photo = notify.file
            async with RequestContent() as req:
                if photo:
                    # 发送带图片的消息
                    resp = await self._send_photo(req, message, photo)
                else:
                    # 发送纯文本消息
                    resp = await self._send_text(req, message)

            self.logger.debug(f"Telegram notification response: {resp.status_code}")
            return resp and resp.status_code == 200

        except Exception as e:
            self.logger.error(f"Telegram 通知发送失败: {e}")
            return False

    async def _send_photo(self, req, message: str, photo) -> Any:
        """发送带图片的消息"""
        data = {
            "chat_id": self.chat_id,
            "caption": message,
            "disable_notification": True,
        }
        return await req.post_data(self.photo_url, data, files={"photo": photo})

    async def _send_text(self, req, message: str) -> Any:
        """发送纯文本消息"""
        data = {
            "chat_id": self.chat_id,
            "text": message,
            "disable_notification": True,
        }
        return await req.post_data(self.message_url, data)
