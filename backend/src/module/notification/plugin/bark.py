from typing import Any, Dict

from module.models import Notification
from module.network import RequestContent
from module.utils.cache_image import str_to_url

from .base_notifier import BaseNotifier


class Notifier(BaseNotifier):
    """Bark 通知器"""

    def __init__(self, token: str, **kwargs):
        super().__init__(token, **kwargs)
        self.notification_url = "https://api.day.app/push"

    def format_message(self, notify: Notification) -> Dict[str, Any]:
        """格式化 Bark 通知消息"""
        data = super().format_message(notify)

        # 处理海报路径
        poster_path = notify.poster_path
        if poster_path:
            if "/" in poster_path:
                poster_path = str_to_url(poster_path.split("/")[-1])

        return {**data, "poster_path": poster_path}

    async def post_msg(self, notify: Notification) -> bool:
        """发送 Bark 通知"""
        try:
            message_data = self.format_message(notify)

            data = {
                "title": message_data["title"],
                "body": message_data["message"],
                "device_key": self.token,
            }

            # 添加图标
            if message_data["poster_path"]:
                data["icon"] = message_data["poster_path"]

            async with RequestContent() as req:
                resp = await req.post_data(self.notification_url, data)

            self.logger.debug(f"Bark notification response: {resp.status_code}")
            return resp and resp.status_code == 200

        except Exception as e:
            self.logger.error(f"Bark 通知发送失败: {e}")
            return False
