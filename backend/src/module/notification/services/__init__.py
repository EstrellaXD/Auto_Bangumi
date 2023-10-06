from types import MappingProxyType
from typing import Dict, Literal, Type, TypeAlias, TypeVar

from .bark import BarkService
from .gotify import GotifyService
from .server_chan import ServerChanService
from .slack import SlackService
from .telegram import TelegramService
from .wecom import WecomService

NotificationType: TypeAlias = Literal[
    "bark",
    "telegram",
    "slack",
    "server-chan",
    "wecom",
    "gotify",
]

NotificationService = TypeVar(
    "NotificationService",
    BarkService,
    ServerChanService,
    TelegramService,
    SlackService,
    WecomService,
    GotifyService,
)

services: Dict[NotificationType, Type[NotificationService]] = MappingProxyType(
    {
        "bark": BarkService,
        "server-chan": ServerChanService,
        "telegram": TelegramService,
        "slack": SlackService,
        "wecom": WecomService,
        "gotify": GotifyService,
    }
)


__all__ = [
    "NotificationService",
    "NotificationType",
    "services",
]
