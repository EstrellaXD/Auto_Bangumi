# from module.conf import settings
# import importlib
# from .base_notifier import Notifier as BaseNotifier


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
# def get_notifier():
#     if settings.notification.enable:
#         notification_type = settings.notification.type
#         package_path = f"module.notification.plugin.{notification_type}"
#     else:
#         package_path = "module.notification.plugin.log_notification"

#     notification: BaseNotifier = importlib.import_module(package_path)
#     Notifier = notification.Notifier
#     return Notifier


# __all__ = [
#     "BarkNotification",
#     "ServerChanNotification",
#     "TelegramNotification",
#     "WecomNotification",
# ]
