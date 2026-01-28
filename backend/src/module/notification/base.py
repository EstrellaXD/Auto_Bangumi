"""Base class for notification providers."""

from abc import ABC, abstractmethod

from module.models.bangumi import Notification
from module.network import RequestContent


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
