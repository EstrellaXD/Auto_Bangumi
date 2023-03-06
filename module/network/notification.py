import requests

from module.conf import settings


class PostNotification:
    def __init__(self):
        self.token = settings.notification_token
        self.notification_url = lambda message: f"https://api.pushbullet.com/v2/{self.token}/{message}"

    def ifttt_post(self, message):
        url = self.notification_url(message)
        response = requests.get(url)
        return response.status_code == 200