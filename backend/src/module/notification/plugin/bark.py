from typing import Any

from pydantic import BaseModel, Field

from module.conf import get_plugin_config
from module.models import Notification
from module.network import RequestContent
from module.utils.cache_image import str_to_url

from .base_notifier import BaseNotifier


class Config(BaseModel):
    token: str = Field(
        default="",
        alias="token",
        description="Telegram bot token, can be obtained from BotFather",
    )

class Notifier(BaseNotifier):
    """Bark 通知器"""

    def __init__(self):
        super().__init__()
        self.notification_url = "https://api.day.app/push"

    def initialize(self) -> None:
        self.config: Config = get_plugin_config(Config(), "notification")
        self.token: str = self.config.token.strip()
        self.photo_url: str = (
            f"https://api.telegram.org/bot{self.config.token}/sendPhoto"
        )
        self.message_url: str = (
            f"https://api.telegram.org/bot{self.config.token}/sendMessage"
        )

    def format_message(self, notify: Notification) -> dict[str, Any]:
        """格式化 Bark 通知消息"""
        poster_path = notify.poster_path
        if poster_path:
            if "/" in poster_path:
                poster_path = str_to_url(poster_path.split("/")[-1])

        notify.poster_path = poster_path

    async def post_msg(self, notify: Notification) -> bool:
        """发送 Bark 通知"""
        try:
            self.format_message(notify)

            data = {
                "title": notify.title,
                "body": notify.message,
                "device_key": self.token,
            }

            # 添加图标
            if notify.poster_path:
                data["icon"] = notify.poster_path

            async with RequestContent() as req:
                resp = await req.post_data(self.notification_url, data)

            self.logger.debug(f"Bark notification response: {resp.status_code}")
            resp.raise_for_status()
            return True

        except Exception as e:
            self.logger.error(f"Bark 通知发送失败: {e}")
            return False
if __name__ == "__main__":
    # 示例用法
    #https://api.day.app/sG7GDikc5iEu5c5iXEuDa4/Icon?icon=https://day.app/assets/images/avatar.jpg
    notifier = Notifier(token="sG7GDikc5iEu5c5iXEuDa4")
    notification = Notification(
        title="测试通知",
        message="这是一个测试消息",
        poster_path="/path/to/poster.jpg"
    )
    success = notifier.post_msg(notification)
    print(f"通知发送成功: {success}")
