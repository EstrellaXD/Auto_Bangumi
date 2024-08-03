import logging

from module.models import Notification

logger = logging.getLogger(__name__)


class LogNotification():

    def __init__(self, token, **kwargs):
        super().__init__()
        self.token = token
        self.notification_url = "https://api.day.app/push"

    async def post_msg(self, notify: Notification) -> bool:
        logger.info(f"{notify.message}")
        return True
