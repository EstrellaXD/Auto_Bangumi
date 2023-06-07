import logging

from module.network import RequestContent

logger = logging.getLogger(__name__)


class ServerChanNotification(RequestContent):
    """Server酱推送"""

    def __init__(self, token, **kwargs):
        super().__init__()
        self.notification_url = f"https://sctapi.ftqq.com/{token}.send"

    def post_msg(self, text: str, title: str) -> bool:
        data = {
            "title": title,
            "desp": text,
        }
        resp = self.post_data(self.notification_url, data)
        logger.debug(f"ServerChan notification: {resp.status_code}")
        return resp.status_code == 200
