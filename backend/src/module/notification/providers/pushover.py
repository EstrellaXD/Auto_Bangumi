"""Pushover notification provider."""

import logging
from typing import TYPE_CHECKING

from module.models.bangumi import Notification
from module.notification.base import NotificationProvider

if TYPE_CHECKING:
    from module.models.config import NotificationProvider as ProviderConfig

logger = logging.getLogger(__name__)


class PushoverProvider(NotificationProvider):
    """Pushover notification provider."""

    API_URL = "https://api.pushover.net/1/messages.json"

    def __init__(self, config: "ProviderConfig"):
        super().__init__()
        self.user_key = config.user_key
        self.api_token = config.api_token

    async def send(self, notification: Notification) -> bool:
        """Send notification via Pushover."""
        message = self._format_message(notification)

        data = {
            "token": self.api_token,
            "user": self.user_key,
            "title": notification.official_title,
            "message": message,
            "html": 0,
        }

        # Add poster as supplementary URL if available
        if notification.poster_path and notification.poster_path != "https://mikanani.me":
            data["url"] = notification.poster_path
            data["url_title"] = "查看海报"

        resp = await self.post_data(self.API_URL, data)
        logger.debug(f"Pushover notification: {resp.status_code}")
        return resp.status_code == 200

    async def test(self) -> tuple[bool, str]:
        """Test Pushover configuration by sending a test message."""
        data = {
            "token": self.api_token,
            "user": self.user_key,
            "title": "AutoBangumi 通知测试",
            "message": "通知测试成功！\nNotification test successful!",
        }
        try:
            resp = await self.post_data(self.API_URL, data)
            if resp.status_code == 200:
                return True, "Pushover test message sent successfully"
            else:
                # Try to parse error message from response
                try:
                    error_data = resp.json()
                    errors = error_data.get("errors", [])
                    if errors:
                        return False, f"Pushover error: {', '.join(errors)}"
                except Exception:
                    pass
                return False, f"Pushover API returned status {resp.status_code}"
        except Exception as e:
            return False, f"Pushover test failed: {e}"
