"""Bark notification provider."""

import logging
from typing import TYPE_CHECKING

from module.models.bangumi import Notification
from module.notification.base import NotificationProvider

if TYPE_CHECKING:
    from module.models.config import NotificationProvider as ProviderConfig

logger = logging.getLogger(__name__)


class BarkProvider(NotificationProvider):
    """Bark (iOS) notification provider."""

    DEFAULT_SERVER = "https://api.day.app"

    def __init__(self, config: "ProviderConfig"):
        super().__init__()
        # Support both legacy token field and new device_key field
        self.device_key = config.device_key or config.token
        server_url = config.server_url or self.DEFAULT_SERVER
        self.notification_url = f"{server_url.rstrip('/')}/push"

    async def send(self, notification: Notification) -> bool:
        """Send notification via Bark."""
        text = self._format_message(notification)
        data = {
            "title": notification.official_title,
            "body": text,
            "icon": notification.poster_path or "",
            "device_key": self.device_key,
        }

        resp = await self.post_data(self.notification_url, data)
        logger.debug(f"Bark notification: {resp.status_code}")
        return resp.status_code == 200

    async def test(self) -> tuple[bool, str]:
        """Test Bark configuration by sending a test notification."""
        data = {
            "title": "AutoBangumi",
            "body": "通知测试成功！\nNotification test successful!",
            "device_key": self.device_key,
        }
        try:
            resp = await self.post_data(self.notification_url, data)
            if resp.status_code == 200:
                return True, "Bark test notification sent successfully"
            else:
                return False, f"Bark API returned status {resp.status_code}"
        except Exception as e:
            return False, f"Bark test failed: {e}"
