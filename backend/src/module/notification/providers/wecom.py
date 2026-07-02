"""WeChat Work (企业微信) notification provider."""

import logging
from typing import TYPE_CHECKING

from module.models.bangumi import Notification
from module.notification.base import NotificationProvider

if TYPE_CHECKING:
    from module.models.config import NotificationProvider as ProviderConfig

logger = logging.getLogger(__name__)


class WecomProvider(NotificationProvider):
    """WeChat Work (企业微信) notification provider using news message format."""

    def __init__(self, config: "ProviderConfig"):
        super().__init__()
        # Support both webhook_url and legacy chat_id field
        self.notification_url = config.webhook_url or config.chat_id
        self.token = config.token

    async def send(self, notification: Notification) -> bool:
        """Send notification via WeChat Work."""
        title = f"【番剧更新】{notification.official_title}"
        msg = self._format_message(notification)

        data = {
            "key": self.token,
            "type": "news",
            "title": title,
            "msg": msg,
        }
        poster_url = self._poster_url(notification)
        if poster_url:
            data["picurl"] = poster_url

        resp = await self.post_data(self.notification_url, data)
        logger.debug("Wecom notification: %s", resp.status_code)
        return resp.status_code == 200

    async def test(self) -> tuple[bool, str]:
        """Test WeChat Work configuration by sending a test message."""
        data = {
            "key": self.token,
            "type": "news",
            "title": "AutoBangumi 通知测试",
            "msg": "通知测试成功！\nNotification test successful!",
        }
        try:
            resp = await self.post_data(self.notification_url, data)
            if resp.status_code == 200:
                return True, "WeChat Work test message sent successfully"
            else:
                return False, f"WeChat Work API returned status {resp.status_code}"
        except Exception as e:
            return False, f"WeChat Work test failed: {e}"
