"""Notification providers registry."""

from typing import TYPE_CHECKING

from module.notification.providers.telegram import TelegramProvider
from module.notification.providers.discord import DiscordProvider
from module.notification.providers.bark import BarkProvider
from module.notification.providers.server_chan import ServerChanProvider
from module.notification.providers.wecom import WecomProvider
from module.notification.providers.gotify import GotifyProvider
from module.notification.providers.pushover import PushoverProvider
from module.notification.providers.webhook import WebhookProvider

if TYPE_CHECKING:
    from module.notification.base import NotificationProvider

# Registry mapping provider type names to their classes
PROVIDER_REGISTRY: dict[str, type["NotificationProvider"]] = {
    "telegram": TelegramProvider,
    "discord": DiscordProvider,
    "bark": BarkProvider,
    "server-chan": ServerChanProvider,
    "serverchan": ServerChanProvider,  # Alternative name
    "wecom": WecomProvider,
    "gotify": GotifyProvider,
    "pushover": PushoverProvider,
    "webhook": WebhookProvider,
}

__all__ = [
    "PROVIDER_REGISTRY",
    "TelegramProvider",
    "DiscordProvider",
    "BarkProvider",
    "ServerChanProvider",
    "WecomProvider",
    "GotifyProvider",
    "PushoverProvider",
    "WebhookProvider",
]
