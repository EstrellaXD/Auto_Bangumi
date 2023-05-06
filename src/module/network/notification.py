import logging

from .request_contents import RequestContent
from module.conf import settings


logger = logging.getLogger(__name__)


class PostNotification:
    def __init__(self):
        self.client = self.getClient()

    @staticmethod
    def getClient():
        if settings.notification.type.lower() == "telegram":
            return TelegramNotification()
        elif settings.notification.type.lower() == "server-chan":
            return ServerChanNotification()
        elif settings.notification.type.lower() == "bark":
            return BarkNotification()
        else:
            return None

    def send_msg(self, title: str, desp: str) -> bool:
        if not settings.notification.enable:
            return False
        if self.client is None:
            return False
        return self.client.send_msg(title, desp)


class TelegramNotification:
    def __init__(self):
        self.token = settings.notification.token
        self.chat_id = settings.notification.chat_id
        self.notification_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def send_msg(self, title: str, desp: str):
        data = {
            "chat_id": settings.notification.chat_id,
            "text": f"{title}\n{desp}",
            "disable_notification": True,
        }
        with RequestContent() as req:
            resp = req.post_data(self.notification_url, data)
            logger.debug(f"Telegram notification: {resp.status_code}")
        return resp.status_code == 200


class ServerChanNotification:
    """Server酱推送"""

    def __init__(self):
        self.token = settings.notification.token
        self.notification_url = f"https://sctapi.ftqq.com/{self.token}.send"

    def send_msg(self, title: str, desp: str) -> bool:
        data = {
            "title": title,
            "desp": desp,
        }
        with RequestContent() as req:
            resp = req.post_data(self.notification_url, data)
            logger.debug(f"ServerChan notification: {resp.status_code}")
        return resp.status_code == 200


class BarkNotification:
    def __init__(self):
        self.token = settings.notification.token
        self.notification_url = "https://api.day.app/push"

    def send_msg(self, title: str, desp: str):
        data = {"title": title, "body": desp, "device_key": self.token}
        with RequestContent() as req:
            resp = req.post_data(self.notification_url, data)
            logger.debug(f"Bark notification: {resp.status_code}")
        return resp.status_code == 200
