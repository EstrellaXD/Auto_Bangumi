import logging
from logging import LogRecord
from types import MappingProxyType
from typing import Dict, Type, TypeVar

from .services import (
    BarkService,
    GotifyService,
    NotificationService,
    ServerChanService,
    SlackService,
    TelegramService,
    WecomService,
)

Notifier = TypeVar(
    "Notifier",
    BarkService,
    ServerChanService,
    TelegramService,
    SlackService,
    WecomService,
    GotifyService,
)

services: Dict[NotificationService, Type[Notifier]] = MappingProxyType(
    {
        "bark": BarkService,
        "server-chan": ServerChanService,
        "telegram": TelegramService,
        "slack": SlackService,
        "wecom": WecomService,
        "gotify": GotifyService,
    }
)


class NotifierHandler(logging.Handler):
    def __init__(self, services=None, **kwargs) -> None:
        super().__init__(**kwargs)

    def emit(self, record: LogRecord) -> None:
        try:
            service = services[record.levelname]
            service.send(record)
        except Exception:
            pass
