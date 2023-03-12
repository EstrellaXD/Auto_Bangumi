import logging

import requests

from module.conf import settings


logger = logging.getLogger(__name__)


class PostNotification:
    def __init__(self):
        self.token = settings.notification_token
        self.notification_url = lambda message: f"https://api.pushbullet.com/v2/{self.token}/{message}"

    def ifttt_post(self, message):
        url = self.notification_url(message)
        response = requests.get(url)
        return response.status_code == 200


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
        try:
            resp = requests.post(self.notification_url, json=data, timeout=3)
            resp.raise_for_status()
        except requests.RequestException as e:
            logging.error("[ServerChanNotification] send fail, error: %s" % e)
            return False
        return True


if __name__ == '__main__':
    name = "勇者、辞职不干了"
    notification = ServerChanNotification()
    notification.send_msg(f"《{name[:10]}》缓存成功", f"[Auto Bangumi]《{name}》缓存成功")
