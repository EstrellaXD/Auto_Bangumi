import asyncio
import logging

from module.conf import settings
from module.database import Database
from module.models import Notification

from .plugin import (
    BarkNotification,
    ServerChanNotification,
    TelegramNotification,
    WecomNotification,
)

logger = logging.getLogger(__name__)


def getClient(type: str):
    if type.lower() == "telegram":
        return TelegramNotification
    elif type.lower() == "server-chan":
        return ServerChanNotification
    elif type.lower() == "bark":
        return BarkNotification
    elif type.lower() == "wecom":
        return WecomNotification
    else:
        return None


class PostNotification:
    def __init__(self):
        Notifier = getClient(settings.notification.type)
        self.notifier = Notifier(
            token=settings.notification.token, chat_id=settings.notification.chat_id
        )

    @staticmethod
    def _get_poster_sync(notify: Notification):
        with Database() as db:
            poster_path = db.bangumi.match_poster(notify.official_title)
        notify.poster_path = poster_path

    async def send_msg(self, notify: Notification) -> bool:
        await asyncio.to_thread(self._get_poster_sync, notify)
        try:
            await self.notifier.post_msg(notify)
            logger.debug(f"Send notification: {notify.official_title}")
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
            return False

    async def __aenter__(self):
        await self.notifier.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.notifier.__aexit__(exc_type, exc_val, exc_tb)
