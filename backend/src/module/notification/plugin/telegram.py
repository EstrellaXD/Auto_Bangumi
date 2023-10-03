import logging

from module.models import Notification
from module.network import RequestContent

logger = logging.getLogger(__name__)


class TelegramNotification(RequestContent):
    def __init__(self, token, chat_id):
        super().__init__()
        self.notification_url = f"https://api.telegram.org/bot{token}/sendPhoto"
        self.chat_id = chat_id

    @staticmethod
    def gen_message(notify: Notification) -> str:
        text = f"""
        番剧名称：{notify.official_title}\n季度： 第{notify.season}季\n更新集数： 第{notify.episode}集
        """
        return text

    def post_msg(self, notify: Notification) -> bool:
        text = self.gen_message(notify)
        data = {
            "chat_id": self.chat_id,
            "caption": text,
            "photo": notify.poster_path,
            "disable_notification": True,
        }
        resp = self.post_data(self.notification_url, data)
        logger.debug(f"Telegram notification: {resp.status_code}")
        return resp.status_code == 200
