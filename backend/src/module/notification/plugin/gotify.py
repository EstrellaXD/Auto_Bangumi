import logging

from module.models import Notification
from module.network import RequestContent
from module.utils import load_image

logger = logging.getLogger(__name__)

class GotifyNotification(RequestContent):
    def __init__(self, token: str, chat_id: str):
        # chat_id is actually endpoint here LUL
        super().__init__()
        self.endpoint = chat_id
        self.header["Authorization"] = f"Bearer {token}"

    @staticmethod
    def gen_message(notify: Notification) -> str:
        text = f"""
        番剧名称：{notify.official_title}\n季度： 第{notify.season}季\n更新集数： 第{notify.episode}集\n![]({notify.poster_path})\n
        """
        return text.strip()

    def post_msg(self, notify: Notification) -> bool:
        data = {
            "title": notify.official_title,
            "message": self.gen_message(notify)
        }
        resp = self.post_data(self.endpoint, data)
        logger.debug(f"Gotify notification: {resp.status_code}")
        return resp.status_code == 200
