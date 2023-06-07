import logging
from module.network import RequestContent


logger = logging.getLogger(__name__)


class BarkNotification(RequestContent):
    def __init__(self, token, **kwargs):
        super().__init__()
        self.token = token
        self.notification_url = "https://api.day.app/push"

    def post_msg(self, text, title: str) -> bool:
        data = {"title": title, "body": text, "device_key": self.token}
        resp = self.post_data(self.notification_url, data)
        logger.debug(f"Bark notification: {resp.status_code}")
        return resp.status_code == 200
