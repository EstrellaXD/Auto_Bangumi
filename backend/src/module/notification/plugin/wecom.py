import logging

from module.network import RequestContent
from module.models import Notification

logger = logging.getLogger(__name__)


class WecomNotification(RequestContent):
    """企业微信推送 基于图文消息"""

    def __init__(self, token, chat_id, **kwargs):
        super().__init__()
        # Chat_id is used as noti_url in this push tunnel
        self.notification_url = f"{chat_id}"
        self.token = token

    @staticmethod
    def gen_message(notify: Notification) -> str:
        text = f"""
        番剧名称：{notify.official_title}\n季度： 第{notify.season}季\n更新集数： 第{notify.episode}集\n{notify.poster_path}\n
        """
        return text

    def post_msg(self, notify: Notification) -> bool:
        ##Change message format to match Wecom push better
        title = "【番剧更新】" + notify.official_title
        msg = self.gen_message(notify)
        picurl = notify.poster_path
        #Default pic to avoid blank in message. Resolution:1068*455
        if picurl == "https://mikanani.me":
            picurl = "https://article.biliimg.com/bfs/article/d8bcd0408bf32594fd82f27de7d2c685829d1b2e.png"
        data = {
            "key":self.token,
            "type": "news",
            "title": title,
            "msg": msg,
            "picurl":picurl
        }
        resp = self.post_data(self.notification_url, data)
        logger.debug(f"Wecom notification: {resp.status_code}")
        return resp.status_code == 200
