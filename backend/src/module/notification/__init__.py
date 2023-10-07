import logging
from typing import Optional, get_args

from module.models.bangumi import Notification

from .services import NotificationService, NotificationType, services

logger = logging.getLogger(__name__)


class NotifierHandler(logging.Handler):
    def __init__(self, service_name: str, **kwargs) -> None:
        notifier_config = kwargs.pop("config", {})
        self.notifier = Notifier(service_name, config=notifier_config)
        super().__init__(**kwargs)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.notifier.send(record=record)
        except Exception as e:
            logger.error(f"Can't send log record to notifier because: {e}")


class Notifier:
    def __init__(self, service_name: str, **kwargs):
        assert service_name in get_args(
            NotificationType
        ), f"Invalid service name: {service_name}"

        notifier_config = kwargs.get("config", {})
        if not notifier_config:
            raise ValueError("Invalid notifier config")

        self.notifier = services[service_name](**notifier_config)

    def _get_poster(self, name: str) -> str:
        # avoid cyclic import
        from module.database import Database

        with Database() as db:
            poster = db.bangumi.match_poster(name)
            return poster

    def send(self, **kwargs) -> bool:
        notification: Optional[Notification] = kwargs.pop("notification", None)
        record: Optional[logging.LogRecord] = kwargs.pop("record", None)
        if notification:
            poster = self._get_poster(notification.official_title)
            notification.poster_path = poster
            data = dict(notification=notification)
        else:
            data = dict(record=record)

        try:
            self.notifier.send(**data)
            logger.debug(f"Send notification: {data}")
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
