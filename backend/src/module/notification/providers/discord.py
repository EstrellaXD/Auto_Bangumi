"""Discord notification provider."""

import logging
from typing import TYPE_CHECKING

from module.models.bangumi import Notification
from module.notification.base import NotificationProvider

if TYPE_CHECKING:
    from module.models.config import NotificationProvider as ProviderConfig

logger = logging.getLogger(__name__)


class DiscordProvider(NotificationProvider):
    """Discord webhook notification provider."""

    def __init__(self, config: "ProviderConfig"):
        super().__init__()
        self.webhook_url = config.webhook_url

    async def send(self, notification: Notification) -> bool:
        """Send notification via Discord webhook."""
        embed = {
            "title": f"📺 {notification.official_title}",
            "description": (
                f"**季度:** 第{notification.season}季\n"
                f"**集数:** 第{notification.episode}集"
            ),
            "color": 0x00BFFF,  # Deep Sky Blue
        }

        # Add poster as thumbnail if a public poster URL is available
        poster_url = self._poster_url(notification)
        if poster_url:
            embed["thumbnail"] = {"url": poster_url}

        data = {
            "embeds": [embed],
        }

        resp = await self._post_json(self.webhook_url, data)
        logger.debug("Discord notification: %s", resp.status_code)
        return resp.status_code in (200, 204)

    async def test(self) -> tuple[bool, str]:
        """Test Discord webhook by sending a test message."""
        embed = {
            "title": "AutoBangumi 通知测试",
            "description": "通知测试成功！\nNotification test successful!",
            "color": 0x00FF00,  # Green
        }
        data = {"embeds": [embed]}

        try:
            resp = await self._post_json(self.webhook_url, data)
            if resp.status_code in (200, 204):
                return True, "Discord test message sent successfully"
            else:
                return False, f"Discord API returned status {resp.status_code}"
        except Exception as e:
            return False, f"Discord test failed: {e}"
