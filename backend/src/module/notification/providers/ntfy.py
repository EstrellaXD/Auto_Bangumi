"""ntfy notification provider."""

import logging
from typing import TYPE_CHECKING

from module.models.bangumi import Notification
from module.notification.base import NotificationProvider

if TYPE_CHECKING:
    from module.models.config import NotificationProvider as ProviderConfig

logger = logging.getLogger(__name__)


class NtfyProvider(NotificationProvider):
    """ntfy notification provider."""

    def __init__(self, config: "ProviderConfig"):
        super().__init__()
        self.server_url = config.server_url.rstrip("/") if config.server_url else "https://ntfy.sh"
        self.topic = config.token  # ntfy uses topic as the identifier
        # For JSON publishing, we POST to the root URL, not the topic URL
        self.notification_url = f"{self.server_url}/"

    async def send(self, notification: Notification) -> bool:
        """Send notification via ntfy using JSON format."""
        message = self._format_message(notification)

        # Build JSON payload according to ntfy API
        data = {
            "topic": self.topic,
            "title": notification.official_title,
            "message": message,
            "priority": 3,  # default priority
            "tags": ["anime", "tv"],
        }

        # Add poster as attachment if available
        if notification.poster_path and notification.poster_path != "https://mikanani.me":
            data["attach"] = notification.poster_path

        try:
            resp = await self.post_json_data(self.notification_url, data)
            if resp is None:
                return False
            logger.debug("ntfy notification: %s", resp.status_code)
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"ntfy notification failed: {e}")
            return False

    async def test(self) -> tuple[bool, str]:
        """Test ntfy configuration by sending a test message."""
        data = {
            "topic": self.topic,
            "title": "AutoBangumi 通知测试",
            "message": "通知测试成功！\nNotification test successful!",
            "priority": 3,
            "tags": ["test"],
        }

        try:
            resp = await self.post_json_data(self.notification_url, data)
            if resp is None:
                return False, "ntfy request failed: connection error"
            if resp.status_code == 200:
                return True, "ntfy test message sent successfully"
            else:
                return False, f"ntfy API returned status {resp.status_code}"
        except Exception as e:
            return False, f"ntfy test failed: {e}"

    async def post_json_data(self, url: str, data: dict):
        """Post JSON data to ntfy."""
        import httpx

        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(
                    url,
                    json=data,
                    headers={"Content-Type": "application/json"},
                    timeout=10.0
                )
                return response
        except httpx.RequestError as e:
            logger.warning(f"ntfy request error: {e}")
            return None