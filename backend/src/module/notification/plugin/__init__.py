from module.conf import settings

from .bark import BarkNotification
from .log_notification import LogNotification
from .server_chan import ServerChanNotification
from .telegram import TelegramNotification
from .wecom import WecomNotification


def getClient(type: str):
    notifiers = {
        "telegram": TelegramNotification,
        "server-chan": ServerChanNotification,
        "bark": BarkNotification,
        "wecom": WecomNotification,
    }
    return notifiers.get(type.lower(), LogNotification)

Notifier =getClient(settings.notification.type)


__all__ = [
    "BarkNotification",
    "ServerChanNotification",
    "TelegramNotification",
    "WecomNotification",
]
