import logging

from module.models import Notification

from .base_notifier import Notifier as BaseNotifier

logger = logging.getLogger(__name__)


class Notifier(BaseNotifier):

    def __init__(self, token, **kwargs):
        pass

    async def post_msg(self, notify: Notification) -> bool:
        logger.info(f"[Notification] {notify.message}")
        return True
