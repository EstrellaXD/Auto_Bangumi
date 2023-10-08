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

        notifier_config = kwargs.pop("config", {})
        if not notifier_config:
            raise ValueError("Invalid notifier config")

        self.notifier = services[service_name](**notifier_config)
        # TODO: add message queue delegate to notifier to send message in background
        # self.q = queue.LifoQueue()

    async def asend(self, **kwargs):
        try:
            await self.notifier.asend(**kwargs)
            # TODO: send message to queue
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")

    def send(self, **kwargs) -> bool:
        try:
            self.notifier.send(**kwargs)
            # TODO: send message to queue
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")

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
