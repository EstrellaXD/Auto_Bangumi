"""Tests for notification: provider registry, manager, and provider implementations."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from module.models import Notification
from module.models.config import NotificationProvider as ProviderConfig
from module.notification import PROVIDER_REGISTRY, NotificationManager
from module.notification.providers import (
    TelegramProvider,
    DiscordProvider,
    BarkProvider,
    ServerChanProvider,
    WecomProvider,
    GotifyProvider,
    PushoverProvider,
    WebhookProvider,
)


# ---------------------------------------------------------------------------
# Provider Registry
# ---------------------------------------------------------------------------


class TestProviderRegistry:
    def test_telegram(self):
        """Registry contains TelegramProvider for 'telegram' type."""
        assert PROVIDER_REGISTRY["telegram"] is TelegramProvider

    def test_discord(self):
        """Registry contains DiscordProvider for 'discord' type."""
        assert PROVIDER_REGISTRY["discord"] is DiscordProvider

    def test_bark(self):
        """Registry contains BarkProvider for 'bark' type."""
        assert PROVIDER_REGISTRY["bark"] is BarkProvider

    def test_server_chan(self):
        """Registry contains ServerChanProvider for 'server-chan' type."""
        assert PROVIDER_REGISTRY["server-chan"] is ServerChanProvider
        assert PROVIDER_REGISTRY["serverchan"] is ServerChanProvider

    def test_wecom(self):
        """Registry contains WecomProvider for 'wecom' type."""
        assert PROVIDER_REGISTRY["wecom"] is WecomProvider

    def test_gotify(self):
        """Registry contains GotifyProvider for 'gotify' type."""
        assert PROVIDER_REGISTRY["gotify"] is GotifyProvider

    def test_pushover(self):
        """Registry contains PushoverProvider for 'pushover' type."""
        assert PROVIDER_REGISTRY["pushover"] is PushoverProvider

    def test_webhook(self):
        """Registry contains WebhookProvider for 'webhook' type."""
        assert PROVIDER_REGISTRY["webhook"] is WebhookProvider

    def test_unknown_type(self):
        """Returns None for unknown notification type."""
        result = PROVIDER_REGISTRY.get("unknown_service")
        assert result is None


# ---------------------------------------------------------------------------
# NotificationManager
# ---------------------------------------------------------------------------


class TestNotificationManager:
    @pytest.fixture
    def mock_settings(self):
        """Mock settings with notification providers."""
        with patch("module.notification.manager.settings") as mock:
            mock.notification.providers = []
            yield mock

    def test_empty_providers(self, mock_settings):
        """Manager handles empty provider list."""
        manager = NotificationManager()
        assert len(manager) == 0

    def test_load_single_provider(self, mock_settings):
        """Manager loads a single enabled provider."""
        config = ProviderConfig(type="telegram", enabled=True, token="test", chat_id="123")
        mock_settings.notification.providers = [config]

        manager = NotificationManager()
        assert len(manager) == 1
        assert isinstance(manager.providers[0], TelegramProvider)

    def test_skip_disabled_provider(self, mock_settings):
        """Manager skips disabled providers."""
        config = ProviderConfig(type="telegram", enabled=False, token="test", chat_id="123")
        mock_settings.notification.providers = [config]

        manager = NotificationManager()
        assert len(manager) == 0

    def test_load_multiple_providers(self, mock_settings):
        """Manager loads multiple enabled providers."""
        configs = [
            ProviderConfig(type="telegram", enabled=True, token="test", chat_id="123"),
            ProviderConfig(type="discord", enabled=True, webhook_url="https://discord.com/webhook"),
            ProviderConfig(type="bark", enabled=True, device_key="device123"),
        ]
        mock_settings.notification.providers = configs

        manager = NotificationManager()
        assert len(manager) == 3
        assert isinstance(manager.providers[0], TelegramProvider)
        assert isinstance(manager.providers[1], DiscordProvider)
        assert isinstance(manager.providers[2], BarkProvider)

    def test_skip_unknown_provider(self, mock_settings):
        """Manager skips unknown provider types."""
        configs = [
            ProviderConfig(type="telegram", enabled=True, token="test", chat_id="123"),
            ProviderConfig(type="unknown_service", enabled=True),
        ]
        mock_settings.notification.providers = configs

        manager = NotificationManager()
        assert len(manager) == 1

    async def test_send_all(self, mock_settings):
        """Manager sends to all providers."""
        configs = [
            ProviderConfig(type="telegram", enabled=True, token="test", chat_id="123"),
            ProviderConfig(type="discord", enabled=True, webhook_url="https://discord.com/webhook"),
        ]
        mock_settings.notification.providers = configs

        manager = NotificationManager()

        # Mock the providers
        for provider in manager.providers:
            provider.send = AsyncMock(return_value=True)
            provider.__aenter__ = AsyncMock(return_value=provider)
            provider.__aexit__ = AsyncMock(return_value=None)

        notify = Notification(official_title="Test Anime", season=1, episode=5)

        with patch.object(manager, "_get_poster", new_callable=AsyncMock):
            await manager.send_all(notify)

        for provider in manager.providers:
            provider.send.assert_called_once_with(notify)

    async def test_test_provider(self, mock_settings):
        """Manager can test a specific provider."""
        config = ProviderConfig(type="telegram", enabled=True, token="test", chat_id="123")
        mock_settings.notification.providers = [config]

        manager = NotificationManager()

        # Mock the provider's test method
        manager.providers[0].test = AsyncMock(return_value=(True, "Test successful"))
        manager.providers[0].__aenter__ = AsyncMock(return_value=manager.providers[0])
        manager.providers[0].__aexit__ = AsyncMock(return_value=None)

        success, message = await manager.test_provider(0)
        assert success is True
        assert message == "Test successful"

    async def test_test_provider_invalid_index(self, mock_settings):
        """Manager handles invalid provider index."""
        mock_settings.notification.providers = []
        manager = NotificationManager()

        success, message = await manager.test_provider(5)
        assert success is False
        assert "Invalid provider index" in message


# ---------------------------------------------------------------------------
# Provider Implementations
# ---------------------------------------------------------------------------


class TestTelegramProvider:
    @pytest.fixture
    def provider(self):
        config = ProviderConfig(type="telegram", enabled=True, token="test_token", chat_id="12345")
        return TelegramProvider(config)

    async def test_send_with_photo(self, provider):
        """Sends photo when poster available."""
        notify = Notification(
            official_title="Test Anime", season=1, episode=5, poster_path="/path/to/poster.jpg"
        )

        with patch.object(provider, "post_files", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            with patch("module.notification.providers.telegram.load_image") as mock_load:
                mock_load.return_value = b"image_data"
                result = await provider.send(notify)

        assert result is True
        mock_post.assert_called_once()

    async def test_send_without_photo(self, provider):
        """Sends text when no poster available."""
        notify = Notification(official_title="Test Anime", season=1, episode=5)

        with patch.object(provider, "post_data", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            with patch("module.notification.providers.telegram.load_image") as mock_load:
                mock_load.return_value = None
                result = await provider.send(notify)

        assert result is True
        mock_post.assert_called_once()

    async def test_test_success(self, provider):
        """Test method sends test message."""
        with patch.object(provider, "post_data", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            success, message = await provider.test()

        assert success is True
        assert "successfully" in message.lower()


class TestDiscordProvider:
    @pytest.fixture
    def provider(self):
        config = ProviderConfig(
            type="discord", enabled=True, webhook_url="https://discord.com/api/webhooks/123"
        )
        return DiscordProvider(config)

    async def test_send(self, provider):
        """Sends embed message."""
        notify = Notification(
            official_title="Test Anime", season=1, episode=5, poster_path="https://example.com/poster.jpg"
        )

        with patch.object(provider, "post_data", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=204)
            result = await provider.send(notify)

        assert result is True
        call_args = mock_post.call_args[0]
        assert "embeds" in call_args[1]


class TestBarkProvider:
    @pytest.fixture
    def provider(self):
        config = ProviderConfig(type="bark", enabled=True, device_key="device123")
        return BarkProvider(config)

    async def test_send(self, provider):
        """Sends push notification."""
        notify = Notification(official_title="Test Anime", season=1, episode=5)

        with patch.object(provider, "post_data", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            result = await provider.send(notify)

        assert result is True
        call_args = mock_post.call_args[0]
        assert "device_key" in call_args[1]


class TestWebhookProvider:
    @pytest.fixture
    def provider(self):
        config = ProviderConfig(
            type="webhook",
            enabled=True,
            url="https://example.com/webhook",
            template='{"anime": "{{title}}", "ep": {{episode}}}',
        )
        return WebhookProvider(config)

    def test_render_template(self, provider):
        """Template rendering replaces variables."""
        notify = Notification(official_title="Test Anime", season=1, episode=5)
        result = provider._render_template(notify)

        assert result["anime"] == "Test Anime"
        assert result["ep"] == 5

    async def test_send(self, provider):
        """Sends custom payload."""
        notify = Notification(official_title="Test Anime", season=1, episode=5)

        with patch.object(provider, "post_data", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            result = await provider.send(notify)

        assert result is True


# ---------------------------------------------------------------------------
# Config Migration
# ---------------------------------------------------------------------------


class TestConfigMigration:
    def test_legacy_config_migration(self):
        """Old single-provider config migrates to new format."""
        from module.models.config import Notification as NotificationConfig

        # Old format
        old_config = NotificationConfig(
            enable=True,
            type="telegram",
            token="old_token",
            chat_id="old_chat_id",
        )

        # Should have migrated to new format
        assert len(old_config.providers) == 1
        assert old_config.providers[0].type == "telegram"
        assert old_config.providers[0].enabled is True

    def test_new_config_no_migration(self):
        """New format with providers doesn't trigger migration."""
        from module.models.config import Notification as NotificationConfig

        provider = ProviderConfig(type="discord", enabled=True, webhook_url="https://discord.com/webhook")
        new_config = NotificationConfig(
            enable=True,
            providers=[provider],
        )

        assert len(new_config.providers) == 1
        assert new_config.providers[0].type == "discord"
