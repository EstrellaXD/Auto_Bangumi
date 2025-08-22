from typing import Any, Dict

from module.models import Message
from module.network import RequestContent, load_image

from .base_notifier import BaseNotifier


class Notifier(BaseNotifier):
    """Telegram 通知器"""

    def __init__(self, **kwargs):
        super().__init__()
        """初始化 Telegram 通知器"""
        self.token:str = kwargs.get("token", "")
        self.chat_id: str = kwargs.get("chat_id", "")
        self.base_url: str = "https://api.telegram.org/bot{token}/"

    def initialize(self) -> None:
        """初始化下载器"""
        pass
        # 加载配置
        # self.config: Config = get_plugin_config(Config(), "notification")
        # self.chat_id:str = self.config.chat_id.strip()
        # self.photo_url: str = (
        #     f"https://api.telegram.org/bot{self.config.token}/sendPhoto"
        # )
        # self.message_url: str = (
        #     f"https://api.telegram.org/bot{self.config.token}/sendMessage"
        # )

    async def post_msg(self, notify: Message) -> bool:
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
        url = f"{self.base_url}sendPhoto".format(token=self.token)
        data = {
            "chat_id": chat_id,
            "caption": message,
            "disable_notification": True,
        }
        return await req.post_data(url, data, files={"photo": photo})

    async def _send_text(self, chat_id,req, message: str) -> Any:
        """发送纯文本消息"""
        url = f"{self.base_url}sendMessage".format(token=self.token)
        data = {
            "chat_id": chat_id,
            "text": message,
            "disable_notification": True,
        }
        return await req.post_data(url, data)
