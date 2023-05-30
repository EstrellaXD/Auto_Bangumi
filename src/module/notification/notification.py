import logging

from .plugin import *

from module.models import Notification
from module.conf import settings


logger = logging.getLogger(__name__)

type = settings.notification.type
token = settings.notification.token
chat_id = settings.notification.chat_id


def getClient():
    if type.lower() == "telegram":
        return TelegramNotification
    elif type.lower() == "server-chan":
        return ServerChanNotification
    elif type.lower() == "bark":
        return BarkNotification
    else:
        return None


class PostNotification(getClient()):
    def send_msg(self, info: Notification) -> bool:
        text = (
            f"番剧名称：{info.official_title}\n"
            f"季度： 第{info.season}季\n"
            f"更新集数： 第{info.episode}集\n"
            f"{info.poster_link}\n"
        )
        try:
            return self.post_msg(text)
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
            return False


if __name__ == "__main__":
    info = Notification(
        official_title="魔法纪录 魔法少女小圆外传",
        season=2,
        episode=1,
        poster_link="https://mikanani.me/images/Bangumi/202107/3788b33f.jpg",
    )
    with PostNotification() as client:
        client.send_msg(info)
