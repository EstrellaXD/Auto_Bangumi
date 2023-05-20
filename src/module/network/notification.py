import logging

from module.network.request_contents import RequestContent
from module.models import Notification
from module.conf import settings


logger = logging.getLogger(__name__)

type = settings.notification.type
token = settings.notification.token
chat_id = settings.notification.chat_id


class TelegramNotification(RequestContent):
    def __init__(self):
        super().__init__()
        self.notification_url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id

    def post_msg(self, text: str) -> bool:
        data = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_notification": True,
        }
        resp = self.post_data(self.notification_url, data)
        logger.debug(f"Telegram notification: {resp.status_code}")
        return resp.status_code == 200


class ServerChanNotification(RequestContent):
    """Server酱推送"""

    def __init__(self):
        super().__init__()
        self.notification_url = f"https://sctapi.ftqq.com/{token}.send"

    def post_msg(self, text: str) -> bool:
        data = {
            "title": "AutoBangumi 番剧更新",
            "desp": text,
        }
        resp = self.post_data(self.notification_url, data)
        logger.debug(f"ServerChan notification: {resp.status_code}")
        return resp.status_code == 200


class BarkNotification(RequestContent):
    def __init__(self):
        super().__init__()
        self.token = token
        self.notification_url = "https://api.day.app/push"

    def post_msg(self, text) -> bool:
        data = {"title": "AutoBangumi 番剧更新", "body": text, "device_key": self.token}
        resp = self.post_data(self.notification_url, data)
        logger.debug(f"Bark notification: {resp.status_code}")
        return resp.status_code == 200


def getClient():
    if type.lower() == "telegram":
        return TelegramNotification
    elif type.lower() == "server-chan":
        return ServerChanNotification
    elif type.lower() == "bark":
        return BarkNotification
    else:
        return None


class PostNotification(getClient()):
    def send_msg(self, info: Notification) -> bool:
        text = (
            f"番剧名称：{info.official_title}\n"
            f"季度： 第{info.season}季\n"
            f"更新集数： 第{info.episode}集\n"
            f"{info.poster_link}\n"
        )
        try:
            return self.post_msg(text)
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
            return False


if __name__ == "__main__":
    info = Notification(
        official_title="魔法纪录 魔法少女小圆外传",
        season=2,
        episode=1,
        poster_link="https://mikanani.me/images/Bangumi/202107/3788b33f.jpg",
    )
    with PostNotification() as client:
        client.send_msg(info)
