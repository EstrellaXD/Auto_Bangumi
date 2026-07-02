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
        super().__init__(config)
        self.url = config.url
        # Narrower than the base class's `str | None` -- webhook always has a
        # rendered template (falls back to DEFAULT_TEMPLATE).
        self.template: str = config.template or DEFAULT_TEMPLATE

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
            "{{poster_url}}": self._poster_url(notification) or "",
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
                "poster_url": self._poster_url(notification) or "",
            }

    async def send(self, notification: Notification) -> bool:
        """Send notification via generic webhook."""
        data = self._render_template(notification)

        resp = await self._post_json(self.url, data)
        logger.debug("Webhook notification: %s", resp.status_code)
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
            resp = await self._post_json(self.url, data)
            if 200 <= resp.status_code < 300:
                return True, "Webhook test request sent successfully"
            else:
                return False, f"Webhook returned status {resp.status_code}"
        except Exception as e:
            return False, f"Webhook test failed: {e}"

    async def _deliver_text(self, title: str, body: str) -> bool:
        """Deliver a system event via webhook (fixed minimal JSON shape).

        System events don't use the user-configured episode template -- it
        expects {{title}}/{{season}}/{{episode}}/{{poster_url}}, which system
        events don't have.
        """
        data = {"title": title, "message": body}
        resp = await self._post_json(self.url, data)
        return 200 <= resp.status_code < 300
