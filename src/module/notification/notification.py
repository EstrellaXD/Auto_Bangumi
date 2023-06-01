import logging

from .plugin import *

from module.models import Notification
from module.conf import settings
from module.database import BangumiDatabase


logger = logging.getLogger(__name__)


def getClient(type=settings.notification.type):
    if type.lower() == "telegram":
        return TelegramNotification
    elif type.lower() == "server-chan":
        return ServerChanNotification
    elif type.lower() == "bark":
        return BarkNotification
    else:
        return None


class PostNotification(getClient()):
    def __init__(self):
        super().__init__(
            token=settings.notification.token,
            chat_id=settings.notification.chat_id
        )

    @staticmethod
    def _gen_message(notify: Notification) -> str:
        with BangumiDatabase() as db:
            poster_path = db.match_poster(notify.official_title)
        if poster_path:
            poster_link = "https://mikanani.me" + poster_path
            text = f"""
            番剧名称：{notify.official_title}\n季度： 第{notify.season}季\n更新集数： 第{notify.episode}集\n{poster_link}\n
            """
        else:
            text = f"""
            番剧名称：{notify.official_title}\n季度： 第{notify.season}季\n更新集数： 第{notify.episode}集\n
            """
        return text

    def send_msg(self, notify: Notification) -> bool:
        text = self._gen_message(notify)
        try:
            self.post_msg(text)
            logger.debug(f"Send notification: {notify.official_title}")
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
            return False


if __name__ == "__main__":
    info = Notification(
        official_title="魔法纪录 魔法少女小圆外传",
        season=2,
        episode=1,
    )
    with PostNotification() as client:
        client.send_msg(info)
