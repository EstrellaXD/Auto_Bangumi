import asyncio
import logging

from module.conf import settings
from module.database import Database
from module.models import Notification
from module.notification.plugin import Notifier

logger = logging.getLogger(__name__)


class PostNotification:

    def __init__(self) -> None:
        self.notifier = Notifier(
            token=settings.notification.token, chat_id=settings.notification.chat_id
        )

    def parse(self, notify: Notification):
        if notify.episode:
            if not notify.poster_path:
                self._get_poster(notify)
            notify.message = f"""
            番剧名称：{notify.title}\n季度： 第{notify.season}季\n更新集数： 第{notify.episode}集
            """.strip()

    @staticmethod
    def _get_poster(notify: Notification):
        with Database() as db:
            poster_path = db.bangumi.match_poster(notify.title)
        notify.poster_path = poster_path

    async def send(self, notify: Notification):
        self.parse(notify)
        try:
            await self.notifier.post_msg(notify)
            logger.debug(f"Send notification: {notify.title}")
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
            return False


if __name__ == "__main__":
    import asyncio

    title = "败犬"
    # link = "posters/aHR0cHM6Ly9pbWFnZS50bWRiLm9yZy90L3Avdzc4MC9wYWRSbWJrMkxkTGd1ZGg1Y0xZMG85VEZ6aEkuanBn"
    nt = Notification(title=title, season=1, episode=2, poster_path=None)
    asyncio.run(PostNotification().send(nt))
