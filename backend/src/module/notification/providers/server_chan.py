"""Server Chan notification provider."""

import logging
from typing import TYPE_CHECKING

from module.models.bangumi import Notification
from module.notification.base import NotificationProvider

if TYPE_CHECKING:
    from module.models.config import NotificationProvider as ProviderConfig

logger = logging.getLogger(__name__)


class ServerChanProvider(NotificationProvider):
    """Server Chan (Server酱) notification provider for WeChat."""

    def __init__(self, config: "ProviderConfig"):
        super().__init__()
        token = config.token
        self.notification_url = f"https://sctapi.ftqq.com/{token}.send"

    async def send(self, notification: Notification) -> bool:
        """Send notification via Server Chan."""
        text = self._format_message(notification)
        data = {
            "title": notification.official_title,
            "desp": text,
        }

        resp = await self.post_data(self.notification_url, data)
        logger.debug(f"ServerChan notification: {resp.status_code}")
        return resp.status_code == 200

    async def test(self) -> tuple[bool, str]:
        """Test Server Chan configuration by sending a test message."""
        data = {
            "title": "AutoBangumi 通知测试",
            "desp": "通知测试成功！\nNotification test successful!",
        }
        try:
            resp = await self.post_data(self.notification_url, data)
            if resp.status_code == 200:
                return True, "Server Chan test message sent successfully"
            else:
                return False, f"Server Chan API returned status {resp.status_code}"
        except Exception as e:
            return False, f"Server Chan test failed: {e}"
