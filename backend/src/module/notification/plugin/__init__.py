# from module.conf import settings

# from .bark import BarkNotification
# from .log_notification import LogNotification
# from .server_chan import ServerChanNotification
# from .telegram import TelegramNotification
# from .wecom import WecomNotification

import importlib
import logging

from module.conf import settings

logger = logging.getLogger(__name__)

notification_type = settings.notification.type
package_path = f"module.notification.plugin.{notification_type}"
notification = importlib.import_module(package_path)
Notification = notification.Notification


# def getClient(type: str):
#     notifiers = {
#         "telegram": TelegramNotification,
#         "server-chan": ServerChanNotification,
#         "bark": BarkNotification,
#         "wecom": WecomNotification,
#     }
#     return notifiers.get(type.lower(), LogNotification)
#
#
# Notifier = getClient(settings.notification.type)


__all__ = [
    "BarkNotification",
    "ServerChanNotification",
    "TelegramNotification",
    "WecomNotification",
]
