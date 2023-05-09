import logging

from module.network.request_contents import RequestContent
from module.models import Notification
from module.conf import settings


logger = logging.getLogger(__name__)


class PostNotification:
    def __init__(self):
        self.type: str = settings.notification.type
        self.token = settings.notification.token
        self.chat_id = settings.notification.chat_id
        self.client = self.getClient()

    def getClient(self):
        if self.type.lower() == "telegram":
            return TelegramNotification(self.token, self.chat_id)
        elif self.type.lower() == "server-chan":
            return ServerChanNotification(self.token)
        elif self.type.lower() == "bark":
            return BarkNotification(self.token)
        else:
            return None

    def send_msg(self, info: Notification) -> bool:
        text = f"番剧名称：{info.official_title}\n" \
               f"季度： 第{info.season}季\n" \
               f"更新集数： 第{info.episode}集\n" \
               f"{info.poster_link}\n"
        if self.client is None:
            return False
        return self.client.send_msg(text)


class TelegramNotification:
    def __init__(self, token, chat_id):
        self.notification_url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id

    def send_msg(self, text: str) -> bool:
        data = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_notification": True,
        }
        with RequestContent() as req:
            resp = req.post_data(self.notification_url, data)
            logger.debug(f"Telegram notification: {resp.status_code}")
        return resp.status_code == 200


class ServerChanNotification:
    """Server酱推送"""

    def __init__(self, token):
        self.notification_url = f"https://sctapi.ftqq.com/{token}.send"

    def send_msg(self, text: str) -> bool:
        data = {
            "title": "AutoBangumi 番剧更新",
            "desp": text,
        }
        with RequestContent() as req:
            resp = req.post_data(self.notification_url, data)
            logger.debug(f"ServerChan notification: {resp.status_code}")
        return resp.status_code == 200


class BarkNotification:
    def __init__(self, token):
        self.token = token
        self.notification_url = "https://api.day.app/push"

    def send_msg(self, text) -> bool:
        data = {"title": "AutoBangumi 番剧更新", "body": text, "device_key": self.token}
        with RequestContent() as req:
            resp = req.post_data(self.notification_url, data)
            logger.debug(f"Bark notification: {resp.status_code}")
        return resp.status_code == 200


if __name__ == '__main__':
    notification = PostNotification()
    info = Notification(
        official_title="魔法纪录 魔法少女小圆外传",
        season=2,
        episode=1,
        poster_link="https://mikanani.me/images/Bangumi/202107/3788b33f.jpg",
    )
    notification.send_msg(info)