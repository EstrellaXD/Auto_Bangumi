import json
import logging
from typing import get_args

from litequeue import SQLQueue
from tenacity import RetryError

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

        from module.conf.const import ROOT

        self._queue = SQLQueue(filename_or_conn=ROOT.joinpath("data", "queue.db"))

    @property
    def q(self) -> SQLQueue:
        return self._queue

    async def asend(self, **kwargs):
        content = kwargs.get("content")
        try:
            await self.notifier.asend(**kwargs)
        except RetryError as e:
            e.reraise()
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
        finally:
            self.q.put(content.json())

    def send(self, **kwargs) -> bool:
        content = kwargs.get("content")
        try:
            self.notifier.send(**kwargs)
        except RetryError as e:
            e.reraise()
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
        finally:
            self.q.put(content.json())

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
