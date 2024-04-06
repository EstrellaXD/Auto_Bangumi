import logging

from module.models import Notification
from module.network import RequestContent

logger = logging.getLogger(__name__)


class DiscordNotification(RequestContent):
    """Use Discord Webhook send notification"""
    API_ENDPOINT = "https://discord.com/api"

    def __init__(self, token, chat_id, **kwargs):
        super().__init__()
        self.notification_url = f"{self.API_ENDPOINT}/webhooks/{chat_id}/{token}"
        self.token = token

    @staticmethod
    def gen_message(notify: Notification) -> str:
        text = f"""
        番剧名称：{notify.official_title}\n季度： 第{notify.season}季\n更新集数： 第{notify.episode}集\n{notify.poster_path}\n
        """
        return text.strip()

    def post_msg(self, notify: Notification) -> bool:
        title = "【番剧更新】" + notify.official_title
        msg = self.gen_message(notify)
        picurl = notify.poster_path

        data = {
            "content": msg,
            "embeds": [
                {
                    "title": title,
                    "image": {
                        "url": picurl
                    }
                }
            ]
        }

        resp = self.post_data(self.notification_url, data)
        logger.debug(f"Discord notification: {resp.status_code}")
        return resp.status_code == 200
