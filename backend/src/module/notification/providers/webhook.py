"""Generic webhook notification provider."""

import json
import logging
import re
from typing import TYPE_CHECKING

from module.models.bangumi import Notification
from module.notification.base import NotificationProvider

if TYPE_CHECKING:
    from module.models.config import NotificationProvider as ProviderConfig

logger = logging.getLogger(__name__)

# Default template for webhook payload
DEFAULT_TEMPLATE = json.dumps(
    {
        "title": "{{title}}",
        "season": "{{season}}",
        "episode": "{{episode}}",
        "poster_url": "{{poster_url}}",
    },
    ensure_ascii=False,
)


class WebhookProvider(NotificationProvider):
    """Generic webhook notification provider with customizable templates."""

    def __init__(self, config: "ProviderConfig"):
        super().__init__()
        self.url = config.url
        self.template = config.template or DEFAULT_TEMPLATE

    def _render_template(self, notification: Notification) -> dict:
        """Render the template with notification data.

        Supported variables:
        - {{title}} - Anime title
        - {{season}} - Season number
        - {{episode}} - Episode number
        - {{poster_url}} - Poster image URL
        """
        rendered = self.template

        # Replace template variables
        replacements = {
            "{{title}}": notification.official_title,
            "{{season}}": str(notification.season),
            "{{episode}}": str(notification.episode),
            "{{poster_url}}": notification.poster_path or "",
        }

        for pattern, value in replacements.items():
            # Escape special characters for JSON string values
            escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
            rendered = rendered.replace(pattern, escaped_value)

        try:
            return json.loads(rendered)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid webhook template JSON: {e}")
            # Fallback to default structure
            return {
                "title": notification.official_title,
                "season": notification.season,
                "episode": notification.episode,
                "poster_url": notification.poster_path or "",
            }

    async def send(self, notification: Notification) -> bool:
        """Send notification via generic webhook."""
        data = self._render_template(notification)

        resp = await self.post_data(self.url, data)
        logger.debug(f"Webhook notification: {resp.status_code}")
        # Accept any 2xx status code as success
        return 200 <= resp.status_code < 300

    async def test(self) -> tuple[bool, str]:
        """Test webhook by sending a test payload."""
        test_notification = Notification(
            official_title="AutoBangumi 通知测试",
            season=1,
            episode=1,
            poster_path="",
        )
        data = self._render_template(test_notification)

        try:
            resp = await self.post_data(self.url, data)
            if 200 <= resp.status_code < 300:
                return True, "Webhook test request sent successfully"
            else:
                return False, f"Webhook returned status {resp.status_code}"
        except Exception as e:
            return False, f"Webhook test failed: {e}"
