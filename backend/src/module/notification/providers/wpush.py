"""WPUSH notification provider."""

import logging
from typing import TYPE_CHECKING

from module.models.bangumi import Notification
from module.notification.base import NotificationProvider

if TYPE_CHECKING:
    from module.models.config import NotificationProvider as ProviderConfig

logger = logging.getLogger(__name__)

API_URL = "https://api.wpush.cn/api/v1/send"
DEFAULT_CHANNEL = "wechat"


class WPushProvider(NotificationProvider):
    """WPUSH multi-channel notification provider.

    Docs: https://wpush.cn/docs
    Success when JSON ``code === 0``.
    """

    def __init__(self, config: "ProviderConfig"):
        super().__init__(config)
        self.apikey = config.token
        self.channel = (config.channel or DEFAULT_CHANNEL).strip() or DEFAULT_CHANNEL
        self.topic_code = (config.topic_code or "").strip()

    def _payload(self, title: str, content: str) -> dict:
        data = {
            "apikey": self.apikey,
            "title": title,
            "content": content,
            "channel": self.channel,
        }
        if self.topic_code:
            data["topic_code"] = self.topic_code
        return data

    def _ok(self, resp) -> bool:
        if resp is None or resp.status_code != 200:
            return False
        try:
            body = resp.json()
        except Exception:
            return False
        return body.get("code") == 0

    async def send(self, notification: Notification) -> bool:
        """Send notification via WPUSH."""
        text = self._format_message(notification)
        resp = await self._post_json(
            API_URL, self._payload(notification.official_title, text)
        )
        logger.debug("WPUSH notification: %s", getattr(resp, "status_code", None))
        return self._ok(resp)

    async def test(self) -> tuple[bool, str]:
        """Test WPUSH configuration by sending a test message."""
        data = self._payload(
            "AutoBangumi 通知测试",
            "通知测试成功！\nNotification test successful!",
        )
        try:
            resp = await self._post_json(API_URL, data)
            if self._ok(resp):
                return True, "WPUSH test message sent successfully"
            try:
                body = resp.json() if resp is not None else {}
            except Exception:
                body = {}
            return False, f"WPUSH API error: {body.get('message') or getattr(resp, 'status_code', 'no response')}"
        except Exception as e:
            return False, f"WPUSH test failed: {e}"

    async def _deliver_text(self, title: str, body: str) -> bool:
        """Deliver a system event via WPUSH."""
        resp = await self._post_json(API_URL, self._payload(title, body))
        return self._ok(resp)
