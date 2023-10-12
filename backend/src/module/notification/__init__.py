import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import get_args

import httpx
from litequeue import SQLQueue
from tenacity import RetryError

from module.models.bangumi import Notification
from module.notification.base import NotificationContent, NotificationWebhook

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

    def _get_json(self, **kwargs):
        content: NotificationContent = kwargs.get("content")
        notification: Notification = kwargs.get("notification")
        record: logging.LogRecord = kwargs.get("record")

        if notification:
            return notification.json()

        if record:
            args = dict(
                name=record.name,
                level=record.levelname,
                pathname=record.pathname,
                lineno=record.lineno,
                msg=record.msg,
            )
            return json.dumps(args)

        if content:
            return content.json()

        raise ValueError(f"Invalid input data: {kwargs}")

    async def asend(self, **kwargs):
        data = self._get_json(**kwargs)
        try:
            await self.notifier.asend(**kwargs)
            self.q.put(data)
        except RetryError as e:
            e.reraise()
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")

    def send(self, **kwargs) -> bool:
        data = self._get_json(**kwargs)
        try:
            self.notifier.send(**kwargs)
            self.q.put(data)
        except RetryError as e:
            e.reraise()
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")

    def send_webhook(self, webhook: NotificationWebhook, **kwargs):
        with ThreadPoolExecutor(max_workers=1) as worker:
            future = worker.submit(httpx.request, **webhook.dict(by_alias=True))

        try:
            ret = future.result()
        except Exception as e:
            logger.warning(f"Failed to send webhook: {e}")
        else:
            logger.debug(f"Webhook response: {ret}")

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
