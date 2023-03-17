import logging

from .request_contents import RequestContent
from module.conf import settings


logger = logging.getLogger(__name__)


class PostNotification:
    def __init__(self):
        self.token = settings.notification_token
        self.notification_url = lambda message: f"https://api.pushbullet.com/v2/{self.token}/{message}"
        self.client = self.getClient()

    @staticmethod
    def getClient():
        if settings.notification.type.lower() == "telegram":
            return TelegramNotification()
        elif settings.notification.type.lower() == "serverchan":
            return ServerChanNotification()
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
        self.token = settings.notification_token
        self.notification_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def send_msg(self, title: str, desp: str) -> bool:
        if not settings.notification_enable:
            return False
        data = {
            "chat_id": settings.notification_chat_id,
            "text": f"{title}\n{desp}",
        }


class ServerChanNotification:
    """Server酱推送"""
    def __init__(self):
        self.token = settings.notification.token
        self.notification_url = f"https://sctapi.ftqq.com/{self.token}.send"

    def send_msg(self, title: str, desp: str) -> bool:
        if not settings.notification.enable:
            return False
        data = {
            "title": title,
            "desp": desp,
        }
        with RequestContent() as req:
            resp = req.post_data(self.notification_url, data)
        return resp.status_code == 200
