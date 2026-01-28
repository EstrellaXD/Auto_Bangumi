"""Gotify notification provider."""

import logging
from typing import TYPE_CHECKING

from module.models.bangumi import Notification
from module.notification.base import NotificationProvider

if TYPE_CHECKING:
    from module.models.config import NotificationProvider as ProviderConfig

logger = logging.getLogger(__name__)


class GotifyProvider(NotificationProvider):
    """Gotify notification provider."""

    def __init__(self, config: "ProviderConfig"):
        super().__init__()
        server_url = config.server_url.rstrip("/")
        self.token = config.token
        self.notification_url = f"{server_url}/message?token={self.token}"

    async def send(self, notification: Notification) -> bool:
        """Send notification via Gotify."""
        message = self._format_message(notification)

        # Build extras for markdown support and image
        extras = {
            "client::display": {"contentType": "text/markdown"},
        }

        if notification.poster_path and notification.poster_path != "https://mikanani.me":
            extras["client::notification"] = {
                "bigImageUrl": notification.poster_path,
            }

        data = {
            "title": notification.official_title,
            "message": message,
            "priority": 5,
            "extras": extras,
        }

        resp = await self.post_data(self.notification_url, data)
        logger.debug(f"Gotify notification: {resp.status_code}")
        return resp.status_code == 200

    async def test(self) -> tuple[bool, str]:
        """Test Gotify configuration by sending a test message."""
        data = {
            "title": "AutoBangumi 通知测试",
            "message": "通知测试成功！\nNotification test successful!",
            "priority": 5,
        }
        try:
            resp = await self.post_data(self.notification_url, data)
            if resp.status_code == 200:
                return True, "Gotify test message sent successfully"
            else:
                return False, f"Gotify API returned status {resp.status_code}"
        except Exception as e:
            return False, f"Gotify test failed: {e}"
