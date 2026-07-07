"""Server Chan notification provider."""

import logging
import re
from typing import TYPE_CHECKING

from module.models.bangumi import Notification
from module.notification.base import NotificationProvider

if TYPE_CHECKING:
    from module.models.config import NotificationProvider as ProviderConfig

logger = logging.getLogger(__name__)

# Server酱³ 的 sendkey 形如 sctp<uid>t<key>，推送端点与 Turbo 版不同 (#904)
_SC3_KEY_RE = re.compile(r"^sctp(\d+)t")


class ServerChanProvider(NotificationProvider):
    """Server Chan (Server酱) notification provider for WeChat."""

    def __init__(self, config: "ProviderConfig"):
        super().__init__(config)
        token = config.token
        sc3 = _SC3_KEY_RE.match(token)
        if sc3:
            self.notification_url = (
                f"https://{sc3.group(1)}.push.ft07.com/send/{token}.send"
            )
        else:
            self.notification_url = f"https://sctapi.ftqq.com/{token}.send"

    async def send(self, notification: Notification) -> bool:
        """Send notification via Server Chan."""
        text = self._format_message(notification)
        data = {
            "title": notification.official_title,
            "desp": text,
        }

        resp = await self.post_data(self.notification_url, data)
        logger.debug("ServerChan notification: %s", resp.status_code)
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

    async def _deliver_text(self, title: str, body: str) -> bool:
        """Deliver a system event via Server Chan."""
        data = {"title": title, "desp": body}
        resp = await self.post_data(self.notification_url, data)
        return resp.status_code == 200
