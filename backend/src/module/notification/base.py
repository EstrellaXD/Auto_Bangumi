"""Base class for notification providers."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from module.conf import settings
from module.models.bangumi import Notification
from module.network import RequestContent
from module.notification.events import SystemEvent

if TYPE_CHECKING:
    from module.models.config import NotificationProvider as ProviderConfig


class NotificationProvider(ABC):
    """Abstract base class for notification providers.

    All notification providers must inherit from this class and implement
    the send() and test() methods. HTTP delivery is composed via a
    ``RequestContent`` instance (``self._http``) rather than inherited -- a
    provider IS-A notification channel, not an HTTP client.
    """

    def __init__(self, config: "ProviderConfig") -> None:
        self._http = RequestContent()
        # 单集通知模板（{{title}}/{{season}}/{{episode}}/{{poster_url}}）；
        # 未设置时 ``_format_message`` 回退到默认中文文案。
        self.template = config.template

    async def __aenter__(self) -> "NotificationProvider":
        await self._http.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._http.__aexit__(exc_type, exc_val, exc_tb)

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

    async def send_event(self, event: SystemEvent) -> bool:
        """Send a system event (RSS failure, download failure, offset review).

        System events use each provider's default title/body delivery
        (:meth:`_deliver_text`) -- the per-episode template only covers
        {{title}}/{{season}}/{{episode}}/{{poster_url}}, which don't apply
        here.

        Args:
            event: The system event to send.

        Returns:
            True if the event was delivered successfully, False otherwise.
        """
        title, body = event.describe()
        return await self._deliver_text(title, body)

    @abstractmethod
    async def _deliver_text(self, title: str, body: str) -> bool:
        """Deliver a plain title + body text message. Backs :meth:`send_event`.

        Args:
            title: Short event title.
            body: Event details.

        Returns:
            True if delivered successfully, False otherwise.
        """
        pass

    def _format_message(self, notify: Notification) -> str:
        """Format the per-episode notification message.

        Uses the provider's configured ``template`` when set, substituting
        ``{{title}}``/``{{season}}``/``{{episode}}``/``{{poster_url}}``;
        otherwise falls back to the default Chinese message (existing
        configs without a template keep this exact text).

        Args:
            notify: The notification data.

        Returns:
            Formatted message string.
        """
        if not self.template:
            return (
                f"番剧名称：{notify.official_title}\n"
                f"季度： 第{notify.season}季\n"
                f"更新集数： 第{notify.episode}集"
            )
        replacements = {
            "{{title}}": notify.official_title,
            "{{season}}": str(notify.season),
            "{{episode}}": str(notify.episode),
            "{{poster_url}}": self._poster_url(notify) or "",
        }
        rendered = self.template
        for pattern, value in replacements.items():
            rendered = rendered.replace(pattern, value)
        return rendered

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

    async def post_data(self, url: str, data: dict):
        """Form-encoded POST, delegating to the composed HTTP client."""
        return await self._http.post_data(url, data)

    async def post_files(self, url: str, data: dict, files: dict):
        """Multipart POST, delegating to the composed HTTP client."""
        return await self._http.post_files(url, data, files)

    async def _post_json(self, url: str, json_data: dict):
        """POST a JSON payload via ``RequestURL.post_json`` (httpx ``json=``).

        Args:
            url: The target URL.
            json_data: The JSON-serializable payload.

        Returns:
            The httpx response.
        """
        return await self._http.post_json(url, json_data)
