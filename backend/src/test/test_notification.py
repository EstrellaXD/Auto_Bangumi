"""Tests for notification: client factory, send_msg, poster lookup."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from module.models import Notification
from module.notification.notification import getClient, PostNotification


# ---------------------------------------------------------------------------
# getClient factory
# ---------------------------------------------------------------------------


class TestGetClient:
    def test_telegram(self):
        """Returns TelegramNotification for 'telegram' type."""
        from module.notification.plugin import TelegramNotification

        result = getClient("telegram")
        assert result is TelegramNotification

    def test_bark(self):
        """Returns BarkNotification for 'bark' type."""
        from module.notification.plugin import BarkNotification

        result = getClient("bark")
        assert result is BarkNotification

    def test_server_chan(self):
        """Returns ServerChanNotification for 'server-chan' type."""
        from module.notification.plugin import ServerChanNotification

        result = getClient("server-chan")
        assert result is ServerChanNotification

    def test_wecom(self):
        """Returns WecomNotification for 'wecom' type."""
        from module.notification.plugin import WecomNotification

        result = getClient("wecom")
        assert result is WecomNotification

    def test_unknown_type(self):
        """Returns None for unknown notification type."""
        result = getClient("unknown_service")
        assert result is None

    def test_case_insensitive(self):
        """Type matching is case-insensitive."""
        from module.notification.plugin import TelegramNotification

        assert getClient("Telegram") is TelegramNotification
        assert getClient("TELEGRAM") is TelegramNotification


# ---------------------------------------------------------------------------
# PostNotification
# ---------------------------------------------------------------------------


class TestPostNotification:
    @pytest.fixture
    def mock_notifier(self):
        """Create a mocked notifier instance."""
        notifier = AsyncMock()
        notifier.post_msg = AsyncMock()
        notifier.__aenter__ = AsyncMock(return_value=notifier)
        notifier.__aexit__ = AsyncMock(return_value=False)
        return notifier

    @pytest.fixture
    def post_notification(self, mock_notifier):
        """Create PostNotification with mocked notifier."""
        with patch("module.notification.notification.settings") as mock_settings:
            mock_settings.notification.type = "telegram"
            mock_settings.notification.token = "test_token"
            mock_settings.notification.chat_id = "12345"
            with patch(
                "module.notification.notification.getClient"
            ) as mock_get_client:
                MockClass = MagicMock()
                MockClass.return_value = mock_notifier
                mock_get_client.return_value = MockClass
                pn = PostNotification()
        pn.notifier = mock_notifier
        return pn

    async def test_send_msg_success(self, post_notification, mock_notifier):
        """send_msg calls notifier.post_msg and succeeds."""
        notify = Notification(official_title="Test Anime", season=1, episode=5)

        with patch.object(PostNotification, "_get_poster_sync"):
            result = await post_notification.send_msg(notify)

        mock_notifier.post_msg.assert_called_once_with(notify)

    async def test_send_msg_failure_no_crash(self, post_notification, mock_notifier):
        """send_msg catches exceptions and returns False."""
        mock_notifier.post_msg.side_effect = Exception("Network error")
        notify = Notification(official_title="Test Anime", season=1, episode=5)

        with patch.object(PostNotification, "_get_poster_sync"):
            result = await post_notification.send_msg(notify)

        assert result is False

    def test_get_poster_sync_sets_path(self):
        """_get_poster_sync queries DB and sets poster_path on notification."""
        notify = Notification(official_title="My Anime", season=1, episode=1)

        with patch("module.notification.notification.Database") as MockDB:
            mock_db = MagicMock()
            mock_db.bangumi.match_poster.return_value = "/posters/my_anime.jpg"
            MockDB.return_value.__enter__ = MagicMock(return_value=mock_db)
            MockDB.return_value.__exit__ = MagicMock(return_value=False)
            PostNotification._get_poster_sync(notify)

        assert notify.poster_path == "/posters/my_anime.jpg"

    def test_get_poster_sync_empty_when_not_found(self):
        """_get_poster_sync sets empty string when no poster found in DB."""
        notify = Notification(official_title="Unknown", season=1, episode=1)

        with patch("module.notification.notification.Database") as MockDB:
            mock_db = MagicMock()
            mock_db.bangumi.match_poster.return_value = ""
            MockDB.return_value.__enter__ = MagicMock(return_value=mock_db)
            MockDB.return_value.__exit__ = MagicMock(return_value=False)
            PostNotification._get_poster_sync(notify)

        assert notify.poster_path == ""
