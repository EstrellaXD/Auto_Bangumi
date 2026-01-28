"""Telegram notification provider."""

import logging
from typing import TYPE_CHECKING

from module.models.bangumi import Notification
from module.notification.base import NotificationProvider
from module.utils import load_image

if TYPE_CHECKING:
    from module.models.config import NotificationProvider as ProviderConfig

logger = logging.getLogger(__name__)


class TelegramProvider(NotificationProvider):
    """Telegram Bot notification provider."""

    def __init__(self, config: "ProviderConfig"):
        super().__init__()
        token = config.token
        self.chat_id = config.chat_id
        self.photo_url = f"https://api.telegram.org/bot{token}/sendPhoto"
        self.message_url = f"https://api.telegram.org/bot{token}/sendMessage"

    async def send(self, notification: Notification) -> bool:
        """Send notification via Telegram."""
        text = self._format_message(notification)
        data = {
            "chat_id": self.chat_id,
            "caption": text,
            "text": text,
            "disable_notification": True,
        }

        photo = load_image(notification.poster_path)
        if photo:
            resp = await self.post_files(self.photo_url, data, files={"photo": photo})
        else:
            resp = await self.post_data(self.message_url, data)

        logger.debug(f"Telegram notification: {resp.status_code}")
        return resp.status_code == 200

    async def test(self) -> tuple[bool, str]:
        """Test Telegram configuration by sending a test message."""
        data = {
            "chat_id": self.chat_id,
            "text": "AutoBangumi 通知测试成功！\nNotification test successful!",
        }
        try:
            resp = await self.post_data(self.message_url, data)
            if resp.status_code == 200:
                return True, "Telegram test message sent successfully"
            else:
                return False, f"Telegram API returned status {resp.status_code}"
        except Exception as e:
            return False, f"Telegram test failed: {e}"
