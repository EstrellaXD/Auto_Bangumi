"""Telegram notification provider."""

import logging
from typing import TYPE_CHECKING

from module.models.bangumi import Notification
from module.notification.base import NotificationProvider
from module.utils import load_image, load_poster_url

if TYPE_CHECKING:
    from module.models.config import NotificationProvider as ProviderConfig

logger = logging.getLogger(__name__)


class TelegramProvider(NotificationProvider):
    """Telegram Bot notification provider."""

    def __init__(self, config: "ProviderConfig"):
        super().__init__(config)
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

        # 发图优先级：源 URL（Telegram 服务端拉图）→ 本地缓存 multipart 上传。
        # 任一失败都降级发纯文本，通知内容不能因海报问题丢失（#1094）。
        resp = None
        photo_url = await load_poster_url(notification.poster_path)
        if photo_url:
            resp = await self.post_data(self.photo_url, {**data, "photo": photo_url})
        if resp is None or resp.status_code != 200:
            photo = await load_image(notification.poster_path)
            if photo:
                resp = await self.post_files(
                    self.photo_url, data, files={"photo": photo}
                )
        if resp is None or resp.status_code != 200:
            if resp is not None:
                logger.warning(
                    "Telegram sendPhoto failed (status %s), falling back to text.",
                    resp.status_code,
                )
            resp = await self.post_data(self.message_url, data)

        if resp is None:
            return False
        logger.debug("Telegram notification: %s", resp.status_code)
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

    async def _deliver_text(self, title: str, body: str) -> bool:
        """Deliver a system event via Telegram."""
        data = {
            "chat_id": self.chat_id,
            "text": f"{title}\n{body}",
            "disable_notification": True,
        }
        resp = await self.post_data(self.message_url, data)
        return resp.status_code == 200
