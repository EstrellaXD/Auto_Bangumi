"""Base class for notification providers."""

from abc import ABC, abstractmethod

from module.conf import settings
from module.models.bangumi import Notification
from module.network import RequestContent
from module.network.request_url import RequestURL


class NotificationProvider(RequestContent, ABC):
    """Abstract base class for notification providers.

    All notification providers must inherit from this class and implement
    the send() and test() methods.
    """

    @abstractmethod
    async def send(self, notification: Notification) -> bool:
        """Send a notification.

        Args:
            notification: The notification data containing anime info.

        Returns:
            True if the notification was sent successfully, False otherwise.
        """
        pass

    @abstractmethod
    async def test(self) -> tuple[bool, str]:
        """Test the notification provider configuration.

        Returns:
            A tuple of (success, message) where success is True if the test
            passed and message contains details about the result.
        """
        pass

    def _format_message(self, notify: Notification) -> str:
        """Format the default notification message.

        Args:
            notify: The notification data.

        Returns:
            Formatted message string.
        """
        return (
            f"番剧名称：{notify.official_title}\n"
            f"季度： 第{notify.season}季\n"
            f"更新集数： 第{notify.episode}集"
        )

    def _poster_url(self, notify: Notification) -> str | None:
        """Build a public poster URL from a locally-stored poster path.

        ``Notification.poster_path`` is a local relative path (e.g.
        ``posters/<hash>.jpg``), not reachable by external services. It can
        only be exposed to providers when a public ``base_url`` is
        configured; otherwise callers must omit the poster field entirely.

        Args:
            notify: The notification data.

        Returns:
            The public poster URL, or None if it cannot be resolved.
        """
        if not notify.poster_path or notify.poster_path == "https://mikanani.me":
            return None
        base_url = settings.notification.base_url
        if not base_url:
            return None
        return f"{base_url.rstrip('/')}/{notify.poster_path}"

    async def _post_json(self, url: str, json_data: dict):
        """POST a JSON payload via ``RequestURL.post_json`` (httpx ``json=``).

        Called explicitly on ``RequestURL`` rather than ``self.post_json``
        because ``RequestContent`` (a parent of this class) defines its own
        unrelated, form-encoded ``post_json`` that would otherwise shadow it.

        Args:
            url: The target URL.
            json_data: The JSON-serializable payload.

        Returns:
            The httpx response.
        """
        return await RequestURL.post_json(self, url, json_data)
