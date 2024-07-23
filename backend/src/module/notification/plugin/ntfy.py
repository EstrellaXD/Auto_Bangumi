import logging

from module.models import Notification
from module.network import RequestContent

logger = logging.getLogger(__name__)


class NtfyNotification(RequestContent):
    def __init__(self, token, chat_id, **kwargs):
        super().__init__()
        
        self.notification_url = f"{chat_id}"
        self.token = token
    
    @staticmethod
    def gen_message(notify: Notification) -> str:
        text = f"""
        番剧名称：{notify.official_title}\n季度： 第{notify.season}季\n更新集数： 第{notify.episode}集\n
        """
        return text.strip()
    
    def post_msg(self, notify: Notification) -> bool:
        text = self.gen_message(notify)
        self.header["Authorization"] = "Bearer " + self.token
        self.header["Title"] = notify.official_title.encode('utf-8')
        # self.header["Icon"] =  notify.poster_path
        data = text.encode('utf-8')
        resp = self.post_data(self.notification_url, data)
        logger.debug(f"ServerChan notification: {resp.status_code}")
        return resp.status_code == 200