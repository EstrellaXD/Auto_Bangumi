import logging
from typing import get_args

from module.conf import settings
from module.database import Database
from module.models.bangumi import Notification

from .services import NotificationService, NotificationType, services

logger = logging.getLogger(__name__)


class NotifierHandler(logging.Handler):
    def __init__(self, service_name: str, **kwargs) -> None:
        notifier_config = kwargs.get("notifier", {})
        if not notifier_config:
            raise ValueError("Invalid notifier config")

        self.notifier = Notifier(service_name, **notifier_config)
        super().__init__(**kwargs)

    def emit(self, record: logging.LogRecord) -> None:
        # TODO: get some information from record and send it by notifier
        try:
            self.notifier.send(record)
        except Exception as e:
            logger.error(f"Notification error: {e}")


class Notifier:
    def __init__(self, service_name: str, **kwargs):
        assert service_name in get_args(
            NotificationService
        ), f"Invalid service name: {service_name}"

        notifier_config = kwargs.get("config", {})
        if not notifier_config:
            raise ValueError("Invalid notifier config")

        self.notifier = services[settings.notification.type](**notifier_config)

    def _get_poster(name: str) -> str:
        with Database() as db:
            poster = db.bangumi.match_poster(name)
            return poster

    def send(self, notification: Notification) -> bool:
        poster = self._get_poster(notification)
        notification.poster_path = poster

        try:
            self.notifier.send(notification)
            logger.debug(f"Send notification: {notification.official_title}")
            return True
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
            return False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


__all__ = [
    "Notifier",
    "NotifierHandler",
    "NotificationService",
    "NotificationType",
    "services",
]
