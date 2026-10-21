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
        super().__init__(config)
        self.device_key = config.device_key
        server_url = config.server_url or self.DEFAULT_SERVER
        self.notification_url = f"{server_url.rstrip('/')}/push"
        # 可选推送参数：只发送已设置的项，旧配置的请求体不变
        self.options = {
            "sound": config.sound,
            "group": config.group,
            "level": config.level,
            "url": config.url,
        }
        self.icon = config.icon

    def _payload(self, title: str, body: str, icon: str | None = None) -> dict:
        data: dict[str, str | None] = {
            "title": title,
            "body": body,
            "device_key": self.device_key,
        }
        data.update({k: v for k, v in self.options.items() if v})
        # 配置的图标优先，其次是调用方给的（单集通知的海报）
        if self.icon or icon:
            data["icon"] = self.icon or icon
        return data

    async def send(self, notification: Notification) -> bool:
        """Send notification via Bark."""
        text = self._format_message(notification)
        data = self._payload(
            notification.official_title, text, self._poster_url(notification)
        )
        resp = await self._post_json(self.notification_url, data)
        logger.debug("Bark notification: %s", resp.status_code)
        return resp.status_code == 200

    async def test(self) -> tuple[bool, str]:
        """Test Bark configuration by sending a test notification."""
        data = self._payload(
            "AutoBangumi", "通知测试成功！\nNotification test successful!"
        )
        try:
            resp = await self._post_json(self.notification_url, data)
            if resp.status_code == 200:
                return True, "Bark test notification sent successfully"
            else:
                return False, f"Bark API returned status {resp.status_code}"
        except Exception as e:
            return False, f"Bark test failed: {e}"

    async def _deliver_text(self, title: str, body: str) -> bool:
        """Deliver a system event via Bark."""
        resp = await self._post_json(self.notification_url, self._payload(title, body))
        return resp.status_code == 200
