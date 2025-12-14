from conf.config import get_config_by_key
from .notification import (
    NotificationProcessor,
    PostNotification,
    get_notification_config,
    set_notification_config,
)
from models.config import Notification as NotificationConfig

__all__ = [
    # 核心通知类
    "PostNotification",
    "NotificationProcessor",
    "get_notification_config",
    # 管理器和配置
]


def init(config: NotificationConfig | None = None):
    if config is None:
        config = get_config_by_key("notification", NotificationConfig)
    set_notification_config(config)

