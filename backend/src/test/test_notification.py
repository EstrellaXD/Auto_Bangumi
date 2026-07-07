"""Tests for notification: provider registry, manager, and provider implementations."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from module.models import Notification
from module.models.config import NotificationProvider as ProviderConfig
from module.network import RequestContent
from module.notification import PROVIDER_REGISTRY, NotificationManager
from module.notification.events import (
    DownloaderUnavailableEvent,
    DownloadFailureEvent,
    OffsetReviewEvent,
    RssFailureEvent,
    UpdateAppliedEvent,
    UpdateAvailableEvent,
)
from module.notification.providers import (
    BarkProvider,
    DiscordProvider,
    GotifyProvider,
    PushoverProvider,
    ServerChanProvider,
    TelegramProvider,
    WebhookProvider,
    WecomProvider,
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
        config = ProviderConfig(
            type="telegram", enabled=True, token="test", chat_id="123"
        )
        mock_settings.notification.providers = [config]

        manager = NotificationManager()
        assert len(manager) == 1
        assert isinstance(manager.providers[0], TelegramProvider)

    def test_skip_disabled_provider(self, mock_settings):
        """Manager skips disabled providers."""
        config = ProviderConfig(
            type="telegram", enabled=False, token="test", chat_id="123"
        )
        mock_settings.notification.providers = [config]

        manager = NotificationManager()
        assert len(manager) == 0

    def test_load_multiple_providers(self, mock_settings):
        """Manager loads multiple enabled providers."""
        configs = [
            ProviderConfig(type="telegram", enabled=True, token="test", chat_id="123"),
            ProviderConfig(
                type="discord", enabled=True, webhook_url="https://discord.com/webhook"
            ),
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
            ProviderConfig(
                type="discord", enabled=True, webhook_url="https://discord.com/webhook"
            ),
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
            provider.send.assert_called_once_with(notify)  # type: ignore[attr-defined]

    async def test_test_provider(self, mock_settings):
        """Manager can test a specific provider."""
        config = ProviderConfig(
            type="telegram", enabled=True, token="test", chat_id="123"
        )
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
        config = ProviderConfig(
            type="telegram", enabled=True, token="test_token", chat_id="12345"
        )
        return TelegramProvider(config)

    async def test_send_with_photo(self, provider):
        """Sends photo when poster available."""
        notify = Notification(
            official_title="Test Anime",
            season=1,
            episode=5,
            poster_path="/path/to/poster.jpg",
        )

        with patch.object(provider, "post_files", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            with patch(
                "module.notification.providers.telegram.load_image"
            ) as mock_load:
                mock_load.return_value = b"image_data"
                result = await provider.send(notify)

        assert result is True
        mock_post.assert_called_once()

    async def test_send_without_photo(self, provider):
        """Sends text when no poster available."""
        notify = Notification(official_title="Test Anime", season=1, episode=5)

        with patch.object(provider, "post_data", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            with patch(
                "module.notification.providers.telegram.load_image"
            ) as mock_load:
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
            type="discord",
            enabled=True,
            webhook_url="https://discord.com/api/webhooks/123",
        )
        return DiscordProvider(config)

    async def test_send(self, provider):
        """Sends embed message."""
        notify = Notification(
            official_title="Test Anime",
            season=1,
            episode=5,
            poster_path="https://example.com/poster.jpg",
        )

        with patch.object(provider, "_post_json", new_callable=AsyncMock) as mock_post:
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

        with patch.object(provider, "_post_json", new_callable=AsyncMock) as mock_post:
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

        with patch.object(provider, "_post_json", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            result = await provider.send(notify)

        assert result is True


# ---------------------------------------------------------------------------
# Composition over inheritance (base.py no longer inherits RequestContent)
# ---------------------------------------------------------------------------


class TestProviderComposition:
    def test_provider_composes_but_does_not_inherit_request_content(self):
        """A provider holds a RequestContent instance rather than being one."""
        config = ProviderConfig(type="bark", enabled=True, device_key="device123")
        provider = BarkProvider(config)

        assert isinstance(provider._http, RequestContent)
        assert not isinstance(provider, RequestContent)


# ---------------------------------------------------------------------------
# Per-episode message templates (base._format_message)
# ---------------------------------------------------------------------------


class TestFormatMessageTemplate:
    def test_format_message_no_template_uses_default_message(self):
        """Without a template, existing configs keep the exact default message."""
        config = ProviderConfig(
            type="gotify", enabled=True, server_url="https://gotify.example", token="t"
        )
        provider = GotifyProvider(config)
        notify = Notification(official_title="Test Anime", season=1, episode=5)

        message = provider._format_message(notify)

        assert message == ("番剧名称：Test Anime\n季度： 第1季\n更新集数： 第5集")

    def test_format_message_with_template_substitutes_variables(self):
        """A configured template replaces {{title}}/{{season}}/{{episode}}."""
        config = ProviderConfig(
            type="gotify",
            enabled=True,
            server_url="https://gotify.example",
            token="t",
            template="{{title}} S{{season}}E{{episode}}",
        )
        provider = GotifyProvider(config)
        notify = Notification(official_title="Test Anime", season=1, episode=5)

        assert provider._format_message(notify) == "Test Anime S1E5"


class TestDiscordTemplate:
    async def test_send_no_template_keeps_default_embed_description(self):
        """No template configured: Discord's default embed text is unchanged."""
        config = ProviderConfig(
            type="discord", enabled=True, webhook_url="https://discord.com/webhook"
        )
        provider = DiscordProvider(config)
        notify = Notification(official_title="Test Anime", season=1, episode=5)

        with patch.object(provider, "_post_json", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=204)
            await provider.send(notify)

        embed = mock_post.call_args[0][1]["embeds"][0]
        assert embed["description"] == "**季度:** 第1季\n**集数:** 第5集"

    async def test_send_with_template_uses_rendered_description(self):
        """A configured template overrides the embed description."""
        config = ProviderConfig(
            type="discord",
            enabled=True,
            webhook_url="https://discord.com/webhook",
            template="{{title}} ep {{episode}}",
        )
        provider = DiscordProvider(config)
        notify = Notification(official_title="Test Anime", season=1, episode=5)

        with patch.object(provider, "_post_json", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=204)
            await provider.send(notify)

        embed = mock_post.call_args[0][1]["embeds"][0]
        assert embed["description"] == "Test Anime ep 5"


# ---------------------------------------------------------------------------
# System events (RSS failure / download failure / offset review)
# ---------------------------------------------------------------------------


class TestSendEvent:
    async def test_send_event_delivers_title_and_body_from_event(self):
        """send_event() formats the event and hands (title, body) to _deliver_text."""
        config = ProviderConfig(type="bark", enabled=True, device_key="device123")
        provider = BarkProvider(config)
        event = RssFailureEvent(
            rss_name="My Feed", rss_url="https://x.example/rss", error="timeout"
        )

        with patch.object(
            provider, "_deliver_text", new_callable=AsyncMock
        ) as mock_deliver:
            mock_deliver.return_value = True
            result = await provider.send_event(event)

        assert result is True
        title, body = mock_deliver.call_args[0]
        assert title == "RSS 订阅连接异常"
        assert "My Feed" in body
        assert "timeout" in body

    async def test_manager_send_event_broadcasts_to_all_providers(self):
        """NotificationManager.send_event fans out to every enabled provider."""
        with patch("module.notification.manager.settings") as mock_settings:
            configs = [
                ProviderConfig(
                    type="telegram", enabled=True, token="test", chat_id="123"
                ),
                ProviderConfig(type="bark", enabled=True, device_key="device123"),
            ]
            mock_settings.notification.providers = configs
            manager = NotificationManager()

        for provider in manager.providers:
            provider.send_event = AsyncMock(return_value=True)
            provider.__aenter__ = AsyncMock(return_value=provider)
            provider.__aexit__ = AsyncMock(return_value=None)

        event = OffsetReviewEvent(official_title="Test Anime", reason="mismatch")
        with (
            patch("module.notification.manager.record_event", new_callable=AsyncMock),
            patch("module.notification.manager.settings") as mock_settings,
        ):
            mock_settings.notification.enable = True
            await manager.send_event(event)

        for provider in manager.providers:
            provider.send_event.assert_called_once_with(  # type: ignore[attr-defined]
                event
            )


class TestEventInboxContract:
    """每个 SystemEvent 提供 kind/severity/once/dedup_key()/payload()，供通知中心持久化。"""

    def test_rss_failure_event_contract(self):
        event = RssFailureEvent(rss_name="Feed", rss_url="http://x/rss", error="boom")
        assert event.kind == "rss_failure"
        assert event.severity == "error"
        assert event.once is False
        assert event.dedup_key() == "rss_failure:http://x/rss"
        assert event.payload() == {
            "rss_name": "Feed",
            "rss_url": "http://x/rss",
            "error": "boom",
        }

    def test_download_failure_event_contract(self):
        event = DownloadFailureEvent(official_title="Anime", torrent_name="t.torrent")
        assert event.kind == "download_failure"
        assert event.severity == "error"
        assert event.dedup_key() == "download_failure:Anime"
        assert event.payload() == {
            "official_title": "Anime",
            "torrent_name": "t.torrent",
        }

    def test_offset_review_event_contract(self):
        event = OffsetReviewEvent(official_title="Anime", reason="mismatch")
        assert event.kind == "offset_review"
        assert event.severity == "warning"
        assert event.dedup_key() == "offset_review:Anime"
        assert event.payload() == {"official_title": "Anime", "reason": "mismatch"}

    def test_downloader_unavailable_event_contract(self):
        event = DownloaderUnavailableEvent(host="http://qb:8080", reason="credentials")
        assert event.kind == "downloader_unavailable"
        assert event.severity == "error"
        assert event.once is False
        # reason 不进 dedup_key：unreachable→credentials 的翻转合并为一条
        assert event.dedup_key() == "downloader:http://qb:8080"
        assert event.payload() == {"host": "http://qb:8080", "reason": "credentials"}
        title, body = event.describe()
        assert "下载器" in title
        assert "密码" in body

    def test_update_available_event_contract(self):
        event = UpdateAvailableEvent(current="3.3.0", latest="3.3.1", channel="beta")
        assert event.kind == "update_available"
        assert event.severity == "info"
        assert event.once is True  # 每个版本只提醒一次，已读后不再重建
        assert event.dedup_key() == "update_available:3.3.1"
        assert event.payload() == {
            "current": "3.3.0",
            "latest": "3.3.1",
            "channel": "beta",
            "notes": "",
        }
        title, body = event.describe()
        assert "3.3.1" in body

    def test_update_applied_event_kind_follows_success(self):
        ok = UpdateAppliedEvent(version="3.3.1", success=True)
        assert ok.kind == "update_applied"
        assert ok.severity == "info"
        assert ok.dedup_key() is None
        assert ok.payload() == {"version": "3.3.1", "message": ""}

        failed = UpdateAppliedEvent(version="3.3.1", success=False, message="sig error")
        assert failed.kind == "update_failed"
        assert failed.severity == "error"
        title, body = failed.describe()
        assert "失败" in title
        assert "sig error" in body


class TestDeliverText:
    """Each provider's own ``_deliver_text`` hook, exercised directly."""

    async def test_bark_deliver_text_posts_title_and_body(self):
        config = ProviderConfig(type="bark", enabled=True, device_key="device123")
        provider = BarkProvider(config)

        with patch.object(provider, "_post_json", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            result = await provider._deliver_text("标题", "正文")

        assert result is True
        data = mock_post.call_args[0][1]
        assert data["title"] == "标题"
        assert data["body"] == "正文"

    async def test_discord_deliver_text_posts_embed(self):
        config = ProviderConfig(
            type="discord", enabled=True, webhook_url="https://discord.com/webhook"
        )
        provider = DiscordProvider(config)

        with patch.object(provider, "_post_json", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=204)
            result = await provider._deliver_text("标题", "正文")

        assert result is True
        embed = mock_post.call_args[0][1]["embeds"][0]
        assert embed["title"] == "标题"
        assert embed["description"] == "正文"

    async def test_gotify_deliver_text_posts_title_and_message(self):
        config = ProviderConfig(
            type="gotify", enabled=True, server_url="https://gotify.example", token="t"
        )
        provider = GotifyProvider(config)

        with patch.object(provider, "_post_json", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            result = await provider._deliver_text("标题", "正文")

        assert result is True
        data = mock_post.call_args[0][1]
        assert data["title"] == "标题"
        assert data["message"] == "正文"

    async def test_pushover_deliver_text_posts_title_and_message(self):
        config = ProviderConfig(
            type="pushover", enabled=True, user_key="u", api_token="a"
        )
        provider = PushoverProvider(config)

        with patch.object(provider, "post_data", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            result = await provider._deliver_text("标题", "正文")

        assert result is True
        data = mock_post.call_args[0][1]
        assert data["title"] == "标题"
        assert data["message"] == "正文"

    async def test_server_chan_deliver_text_posts_title_and_desp(self):
        config = ProviderConfig(type="server-chan", enabled=True, token="t")
        provider = ServerChanProvider(config)

        with patch.object(provider, "post_data", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            result = await provider._deliver_text("标题", "正文")

        assert result is True
        data = mock_post.call_args[0][1]
        assert data["title"] == "标题"
        assert data["desp"] == "正文"

    def test_server_chan_legacy_key_uses_sctapi_endpoint(self):
        config = ProviderConfig(type="server-chan", enabled=True, token="SCT123abc")
        provider = ServerChanProvider(config)

        assert provider.notification_url == "https://sctapi.ftqq.com/SCT123abc.send"

    def test_server_chan_sc3_key_uses_ft07_endpoint(self):
        """Server酱³ 的 sendkey 以 sctp<uid>t 开头，走 push.ft07.com 端点 (#904)。"""
        config = ProviderConfig(type="server-chan", enabled=True, token="sctp456tXYZ")
        provider = ServerChanProvider(config)

        assert (
            provider.notification_url
            == "https://456.push.ft07.com/send/sctp456tXYZ.send"
        )

    def test_server_chan_malformed_sctp_key_falls_back_to_legacy(self):
        config = ProviderConfig(type="server-chan", enabled=True, token="sctpXYZ")
        provider = ServerChanProvider(config)

        assert provider.notification_url == "https://sctapi.ftqq.com/sctpXYZ.send"

    async def test_telegram_deliver_text_posts_combined_text(self):
        config = ProviderConfig(
            type="telegram", enabled=True, token="test_token", chat_id="12345"
        )
        provider = TelegramProvider(config)

        with patch.object(provider, "post_data", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            result = await provider._deliver_text("标题", "正文")

        assert result is True
        data = mock_post.call_args[0][1]
        assert data["text"] == "标题\n正文"

    async def test_webhook_deliver_text_posts_title_and_message(self):
        config = ProviderConfig(
            type="webhook", enabled=True, url="https://example.com/webhook"
        )
        provider = WebhookProvider(config)

        with patch.object(provider, "_post_json", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            result = await provider._deliver_text("标题", "正文")

        assert result is True
        data = mock_post.call_args[0][1]
        assert data == {"title": "标题", "message": "正文"}

    async def test_wecom_deliver_text_posts_title_and_msg(self):
        config = ProviderConfig(
            type="wecom", enabled=True, webhook_url="https://wecom.example/webhook"
        )
        provider = WecomProvider(config)

        with patch.object(provider, "post_data", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            result = await provider._deliver_text("标题", "正文")

        assert result is True
        data = mock_post.call_args[0][1]
        assert data["title"] == "标题"
        assert data["msg"] == "正文"


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

        provider = ProviderConfig(
            type="discord", enabled=True, webhook_url="https://discord.com/webhook"
        )
        new_config = NotificationConfig(
            enable=True,
            providers=[provider],
        )

        assert len(new_config.providers) == 1
        assert new_config.providers[0].type == "discord"
