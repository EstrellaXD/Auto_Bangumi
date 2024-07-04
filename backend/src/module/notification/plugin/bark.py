import logging
from typing import Optional

from module.models import Notification
from module.network import RequestContent

logger = logging.getLogger(__name__)


class BarkNotification(RequestContent):
    def __init__(
        self,
        token: str,
        bark_params: Optional[dict],
        bark_server: Optional[str],
        **kwargs,
    ) -> None:
        super().__init__()
        self.token = token
        self.params = bark_params
        if bark_server is not None:
            if not bark_server.startswith("http"):
                bark_server = "https://" + bark_server
            if not bark_server.endswith("push"):
                bark_server = bark_server.rstrip("/") + "/push"

            self.notification_url = bark_server
        else:
            self.notification_url = "https://api.day.app/push"

    @staticmethod
    def gen_message(notify: Notification) -> str:
        text = f"""
        番剧名称：{notify.official_title}\n季度： 第{notify.season}季\n更新集数： 第{notify.episode}集\n{notify.poster_path}\n
        """
        return text.strip()

    def post_msg(self, notify: Notification) -> bool:
        text = self.gen_message(notify)
        data = {
            "title": notify.official_title,
            "body": text,
            "icon": notify.poster_path,
            "device_key": self.token,
        }
        if isinstance(self.params, dict):
            data.update(self.params)
        resp = self.post_data(self.notification_url, data)
        logger.debug(f"Bark notification: {resp.status_code}")
        return resp.status_code == 200
