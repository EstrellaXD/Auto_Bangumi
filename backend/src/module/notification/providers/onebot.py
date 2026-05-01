"""OneBot v11 notification provider.

OneBot v11 is a standard for QQ bot APIs. This provider sends
notifications via the OneBot v11 HTTP API.

Documentation: https://github.com/botuniverse/onebot-11
"""

import base64
import json
import logging
import os
from typing import TYPE_CHECKING

from module.models.bangumi import Notification
from module.notification.base import NotificationProvider

if TYPE_CHECKING:
    from module.models.config import NotificationProvider as ProviderConfig

logger = logging.getLogger(__name__)


class OneBotProvider(NotificationProvider):
    """OneBot v11 HTTP API notification provider.

    Sends anime update notifications through a OneBot v11-compatible
    QQ bot using the HTTP API.

    Config fields used:
        - url: Base URL of the OneBot HTTP API (e.g. http://localhost:5700)
        - token: Optional Authorization access_token
        - chat_id: Target user_id (private) or group_id (group)
        - message_type: "private" for private messages, "group" for group messages
    """

    def __init__(self, config: "ProviderConfig"):
        super().__init__()
        self.base_url = config.url.rstrip("/")
        self.token = config.token or ""
        self.chat_id = config.chat_id or ""
        self.message_type = config.message_type or "private"

        # Build API endpoints
        self.private_msg_url = f"{self.base_url}/send_private_msg"
        self.group_msg_url = f"{self.base_url}/send_group_msg"

        # Build JSON headers (OneBot API expects application/json)
        self.json_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.token:
            self.json_headers["Authorization"] = f"Bearer {self.token}"

    async def _post_json(self, url: str, data: dict) -> object:
        """Send a JSON POST request using the shared httpx client.

        OneBot API requires proper application/json content type,
        which the inherited post_data() does not provide (it sends
        form-encoded data). This method uses the underlying httpx
        client directly with json= parameter.

        Args:
            url: The URL to send the request to.
            data: The JSON-serializable data to send.

        Returns:
            The httpx response object, or None on failure.
        """
        try:
            req = await self._client.post(
                url=url,
                json=data,
                headers=self.json_headers,
            )
            req.raise_for_status()
            return req
        except Exception as e:
            logger.warning(f"[OneBot] Request failed: {e}")
            return None

    def _get_image_file(self, poster_path: str) -> str | None:
        """Convert poster_path to a OneBot-compatible image file reference.

        Handles three cases:
        1. Remote URL (contains ://) - use as-is
        2. Local file path - read and convert to base64
        3. Invalid/missing - return None

        Args:
            poster_path: The poster path or URL from the database.

        Returns:
            A OneBot-compatible file string (URL or base64), or None.
        """
        if not poster_path or poster_path in ("", "https://mikanani.me"):
            return None

        # If it's a remote URL, use it directly
        if "://" in poster_path:
            return poster_path

        # Otherwise, try to read it as a local file
        # The path is relative to the data directory (e.g. "posters/xxx.jpg")
        local_path = os.path.join("data", poster_path.lstrip("/"))
        if os.path.exists(local_path):
            try:
                with open(local_path, "rb") as f:
                    img_data = f.read()
                img_b64 = base64.b64encode(img_data).decode("ascii")
                # Determine MIME type from extension
                ext = os.path.splitext(local_path)[1].lower()
                mime_map = {
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png": "image/png",
                    ".gif": "image/gif",
                    ".webp": "image/webp",
                }
                mime = mime_map.get(ext, "image/jpeg")
                return f"base64://{img_b64}"
            except Exception as e:
                logger.warning(f"[OneBot] Failed to read local image {local_path}: {e}")
                return None
        else:
            logger.warning(f"[OneBot] Local image not found: {local_path}")
            return None

    def _build_payload(
        self, text: str, poster_path: str = None
    ) -> str | list:
        """Build the message payload for OneBot API.

        For plain text (no poster), sends a simple string.
        When a poster image is available, sends a message segment array
        with both image and text.

        Args:
            text: The text message content.
            poster_path: Optional URL or local path to a poster image.

        Returns:
            A string (plain text) or list (message segments).
        """
        image_file = self._get_image_file(poster_path) if poster_path else None
        if image_file:
            return [
                {"type": "image", "data": {"file": image_file}},
                {"type": "text", "data": {"text": text}},
            ]
        return text

    async def send(self, notification: Notification) -> bool:
        """Send notification via OneBot v11.

        Args:
            notification: The notification data.

        Returns:
            True if the message was sent successfully.
        """
        text = self._format_message(notification)
        message = self._build_payload(text, notification.poster_path)

        if self.message_type == "group":
            payload = {
                "group_id": int(self.chat_id),
                "message": message,
            }
            url = self.group_msg_url
        else:
            payload = {
                "user_id": int(self.chat_id),
                "message": message,
            }
            url = self.private_msg_url

        resp = await self._post_json(url, payload)
        logger.debug("OneBot notification: %s", resp.status_code if resp else None)

        if resp and resp.status_code == 200:
            try:
                result = resp.json()
                if result.get("status") == "ok" or result.get("retcode") == 0:
                    return True
                else:
                    logger.warning("OneBot API returned error: %s", result)
                    return False
            except (json.JSONDecodeError, AttributeError):
                return True

        return resp is not None and resp.status_code == 200

    async def test(self) -> tuple[bool, str]:
        """Test the OneBot configuration by sending a test message.

        Returns:
            A tuple of (success, message).
        """
        text = "AutoBangumi 通知测试成功！\nNotification test successful!"

        if self.message_type == "group":
            payload = {
                "group_id": int(self.chat_id),
                "message": text,
            }
            url = self.group_msg_url
        else:
            payload = {
                "user_id": int(self.chat_id),
                "message": text,
            }
            url = self.private_msg_url

        try:
            resp = await self._post_json(url, payload)
            if resp and resp.status_code == 200:
                try:
                    result = resp.json()
                    if result.get("status") == "ok" or result.get("retcode") == 0:
                        return True, "OneBot test message sent successfully"
                    else:
                        error_msg = (
                            result.get("msg")
                            or result.get("wording")
                            or "unknown error"
                        )
                        return False, f"OneBot API error: {error_msg}"
                except (json.JSONDecodeError, AttributeError):
                    return True, "OneBot test message sent successfully"
            else:
                status = resp.status_code if resp else "No response"
                return False, f"OneBot API returned status {status}"
        except Exception as e:
            return False, f"OneBot test failed: {e}"
