import logging
import apprise
import os

from module.conf import settings
from module.database import Database
from module.models import Notification

logger = logging.getLogger(__name__)

class PostNotification:
    def __init__(self):
        self.apobj = apprise.Apprise()
        self.apobj.add(settings.notification.entry)

    @staticmethod
    def _get_poster(notify: Notification):
        with Database() as db:
            poster_path = db.bangumi.match_poster(notify.official_title)
        poster_path = f"data/{poster_path}"
        if not os.path.isfile(poster_path):
            poster_path = None
        notify.poster_path = poster_path

    def send_msg(self, notify: Notification) -> bool:
        self._get_poster(notify)

        try:
            self.apobj.notify(
                title=f'番剧更新：{notify.official_title}',
                body=f'第 {notify.season} 季，第 {notify.episode} 话',
                attach=notify.poster_path
            )
            logger.debug(f"Send notification: {notify.official_title}")
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
            return False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass