"""Tests for configuration: loading, env overrides, defaults, migration."""

import json
import os
from unittest.mock import patch

import pytest

from module.conf.config import Settings
from module.models.config import (
    Config,
    DownloaderOptions,
    NotificationProvider,
    RSSParser,
    Security,
)
from module.models.config import (
    Notification as NotificationConfig,
)

# ---------------------------------------------------------------------------
# Config model defaults
# ---------------------------------------------------------------------------


class TestConfigDefaults:
    def test_program_defaults(self):
        """Program has correct default values."""
        config = Config()
        assert config.program.rss_time == 900
        assert config.program.rename_time == 60
        assert config.program.webui_port == 7892

    def test_downloader_defaults(self):
        """Downloader has correct default values."""
        config = Config()
        assert config.downloader.type == "qbittorrent"
        assert config.downloader.path == "/downloads/Bangumi"
        assert config.downloader.ssl is False

    def test_rss_parser_defaults(self):
        """RSSParser has correct default values."""
        config = Config()
        assert config.rss_parser.enable is True
        assert config.rss_parser.language == "zh"
        assert config.rss_parser.engine == "classic"
        assert "720" in config.rss_parser.filter

    @pytest.mark.parametrize("engine", ["classic", "tokenizer"])
    def test_rss_parser_accepts_supported_engines(self, engine):
        """RSSParser accepts the stable and Preview engine identifiers."""
        parser = RSSParser.model_validate({"engine": engine})
        assert parser.engine == engine

    def test_rss_parser_rejects_unknown_engine(self):
        """Unknown engines are rejected instead of silently falling back."""
        with pytest.raises(ValueError):
            RSSParser.model_validate({"engine": "preview"})

    def test_bangumi_manage_defaults(self):
        """BangumiManage has correct default values."""
        config = Config()
        assert config.bangumi_manage.enable is True
        assert config.plugins.slots.rename_strategy == "pn"
        assert config.bangumi_manage.group_tag is False
        assert config.bangumi_manage.remove_bad_torrent is False
        assert config.plugins.slots.conflict_policy == "hold"
        assert config.bangumi_manage.eps_complete is False

    def test_proxy_defaults(self):
        """Proxy is disabled by default."""
        config = Config()
        assert config.proxy.enable is False
        assert config.proxy.type == "http"

    def test_notification_defaults(self):
        """Notification is disabled by default with empty providers."""
        config = Config()
        assert config.notification.enable is False
        assert config.notification.providers == []


# ---------------------------------------------------------------------------
# Config serialization
# ---------------------------------------------------------------------------


class TestPluginInstances:
    @pytest.mark.parametrize(
        "plugins",
        [
            {"slots": {"downloader": "missing"}},
            {
                "instances": [
                    {"id": "default", "point": "downloader", "provider": "qb"},
                    {"id": "default", "point": "downloader", "provider": "aria2"},
                ]
            },
            {
                "instances": [
                    {
                        "id": "default",
                        "point": "downloader",
                        "provider": "qbittorrent",
                        "options": {"ssl": "sometimes"},
                    }
                ]
            },
        ],
    )
    def test_invalid_downloader_instances_rejected(self, plugins):
        with pytest.raises(ValueError):
            Config.model_validate({"plugins": plugins})

    def test_downloader_view_follows_slot(self):
        config = Config.model_validate(
            {
                "plugins": {
                    "slots": {"downloader": "nas"},
                    "instances": [
                        {"id": "default", "point": "downloader", "provider": "qb"},
                        {
                            "id": "nas",
                            "point": "downloader",
                            "provider": "aria2",
                            "options": {"host": "nas:6800"},
                        },
                    ],
                }
            }
        )
        assert (config.downloader.id, config.downloader.type) == ("nas", "aria2")
        assert config.downloader.host == "nas:6800"
        # 未填写的字段取默认值
        assert config.downloader.path == "/downloads/Bangumi"


class TestConfigSerialization:
    def test_dict_uses_alias(self):
        """Config.dict() uses field aliases (by_alias=True)."""
        config = Config()
        d = config.dict()
        # 下载器实例的 options 用别名 host 而不是 host_
        options = d["plugins"]["instances"][0]["options"]
        assert "host" in options
        assert "host_" not in options

    def test_roundtrip_json(self, tmp_path):
        """Config can be serialized to JSON and loaded back."""
        config = Config()
        config_dict = config.dict()
        json_path = tmp_path / "config.json"
        with open(json_path, "w") as f:
            json.dump(config_dict, f)

        with open(json_path, "r") as f:
            loaded = json.load(f)

        loaded_config = Config.model_validate(loaded)
        assert loaded_config.program.rss_time == config.program.rss_time
        assert loaded_config.downloader.type == config.downloader.type
        assert loaded_config.rss_parser.engine == "classic"


# ---------------------------------------------------------------------------
# Settings._migrate_old_config
# ---------------------------------------------------------------------------


class TestMigrateOldConfig:

    def test_no_migration_needed(self):
        """Already-current config passes through unchanged."""
        current_config = {
            "program": {"rss_time": 900, "rename_time": 60},
            "rss_parser": {"enable": True},
        }
        result = Settings._migrate_old_config(current_config)
        assert result["program"]["rss_time"] == 900
        assert result["program"]["rename_time"] == 60


# ---------------------------------------------------------------------------
# Settings.load from file
# ---------------------------------------------------------------------------


class TestSettingsLoad:
    def test_load_from_json_file(self, tmp_path):
        """Settings loads config from a JSON file when it exists."""
        config_data = Config().dict()
        config_data["program"]["rss_time"] = 1200  # Custom value
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        with patch("module.conf.config.CONFIG_PATH", config_file):
            with patch("module.conf.config.VERSION", "3.2.0"):
                s = Settings.__new__(Settings)
                Config.__init__(s)
                s.load()

        assert s.program.rss_time == 1200

    def test_load_legacy_config_defaults_parser_engine_to_classic(self, tmp_path):
        """A config written before engine existed keeps Classic behaviour."""
        config_data = Config().dict()
        config_data["rss_parser"].pop("engine", None)
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        with patch("module.conf.config.CONFIG_PATH", config_file):
            s = Settings.__new__(Settings)
            Config.__init__(s)
            s.load()

        assert s.rss_parser.engine == "classic"

    def test_save_writes_json(self, tmp_path):
        """settings.save() writes valid JSON to CONFIG_PATH."""
        config_file = tmp_path / "config_out.json"

        with patch("module.conf.config.CONFIG_PATH", config_file):
            s = Settings.__new__(Settings)
            Config.__init__(s)
            s.save()

        assert config_file.exists()
        with open(config_file) as f:
            data = json.load(f)
        assert "program" in data
        assert "downloader" not in data
        assert data["plugins"]["instances"][0]["provider"] == "qbittorrent"
        # 新配置文件包含 llm 段
        assert "llm" in data
        assert data["rss_parser"]["engine"] == "classic"

    def test_removed_legacy_sections_are_dropped_on_save(self, tmp_path):
        """3.3 遗留的 experimental_openai / 通知旧字段不再进入运行时，也不会被写回。"""
        config_data = Config().dict()
        config_data["experimental_openai"] = {"enable": True, "api_key": "sk-old"}
        config_data["notification"].update({"type": "telegram", "token": "t"})
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))

        with patch("module.conf.config.CONFIG_PATH", config_file):
            s = Settings.__new__(Settings)
            Config.__init__(s)
            s.load()
            s.save()

        saved = json.loads(config_file.read_text())
        assert "experimental_openai" not in saved
        assert "type" not in saved["notification"]
        assert "token" not in saved["notification"]


# ---------------------------------------------------------------------------
# Environment variable overrides
# ---------------------------------------------------------------------------


class TestEnvOverrides:
    def test_downloader_env_maps_onto_default_instance(self, tmp_path):
        """AB_DOWNLOADER_* / AB_DOWNLOAD_PATH / AB_METHOD 写入默认下载器实例与 slots。"""
        config_file = tmp_path / "config.json"

        env = {
            "AB_DOWNLOADER_HOST": "192.168.1.100:9090",
            "AB_DOWNLOADER_USERNAME": "ab",
            "AB_DOWNLOADER_PASSWORD": "pw",
            "AB_DOWNLOAD_PATH": "/data/Bangumi",
            "AB_METHOD": "Advance",
        }
        with patch.dict(os.environ, env, clear=False):
            with patch("module.conf.config.CONFIG_PATH", config_file):
                s = Settings.__new__(Settings)
                Config.__init__(s)
                s.init()

        assert (s.downloader.host, s.downloader.username, s.downloader.password) == (
            "192.168.1.100:9090",
            "ab",
            "pw",
        )
        assert s.downloader.path == "/data/Bangumi"
        assert s.downloader.type == "qbittorrent"
        assert s.plugins.slots.rename_strategy == "advance"
        saved = json.loads(config_file.read_text())
        assert "downloader" not in saved
        assert len(saved["plugins"]["instances"]) == 1

    def test_rss_parser_engine_from_env(self, tmp_path):
        """AB_RSS_PARSER_ENGINE selects a supported parser engine."""
        config_file = tmp_path / "config.json"

        with patch.dict(os.environ, {"AB_RSS_PARSER_ENGINE": "TOKENIZER"}, clear=False):
            with patch("module.conf.config.CONFIG_PATH", config_file):
                s = Settings.__new__(Settings)
                Config.__init__(s)
                s.init()

        assert s.rss_parser.engine == "tokenizer"

    def test_revision_conflict_policy_from_env(self, tmp_path):
        config_file = tmp_path / "config.json"

        with patch.dict(
            os.environ,
            {"AB_REVISION_CONFLICT_POLICY": "REPLACE"},
            clear=False,
        ):
            with patch("module.conf.config.CONFIG_PATH", config_file):
                s = Settings.__new__(Settings)
                Config.__init__(s)
                s.init()

        assert s.plugins.slots.conflict_policy == "replace"


# ---------------------------------------------------------------------------
# Security model
# ---------------------------------------------------------------------------


class TestSecurityModel:
    def test_security_defaults(self):
        """Security has empty whitelists and token lists by default."""
        sec = Security()
        assert sec.login_whitelist == []
        assert sec.login_tokens == []
        assert sec.mcp_whitelist == []
        assert sec.mcp_tokens == []

    def test_security_in_config(self):
        """Config includes a Security section with correct defaults."""
        config = Config()
        assert hasattr(config, "security")
        assert isinstance(config.security, Security)
        assert config.security.login_whitelist == []

    def test_security_populated(self):
        """Security fields accept lists of CIDRs and tokens."""
        sec = Security(
            login_whitelist=["192.168.0.0/16"],
            login_tokens=["token-abc"],
            mcp_whitelist=["10.0.0.0/8"],
            mcp_tokens=["mcp-secret"],
        )
        assert "192.168.0.0/16" in sec.login_whitelist
        assert "token-abc" in sec.login_tokens
        assert "10.0.0.0/8" in sec.mcp_whitelist
        assert "mcp-secret" in sec.mcp_tokens

    def test_security_roundtrip_serialization(self):
        """Security serializes and deserializes correctly."""
        original = Security(
            login_whitelist=["127.0.0.0/8"],
            mcp_tokens=["tok1"],
        )
        data = original.model_dump()
        restored = Security.model_validate(data)
        assert restored.login_whitelist == ["127.0.0.0/8"]
        assert restored.mcp_tokens == ["tok1"]


# ---------------------------------------------------------------------------
# NotificationProvider model
# ---------------------------------------------------------------------------


class TestNotificationProvider:
    def test_minimal_provider(self):
        """NotificationProvider requires only type."""
        p = NotificationProvider(type="telegram")
        assert p.type == "telegram"
        assert p.enabled is True

    def test_telegram_provider_fields(self):
        """Telegram provider stores token and chat_id."""
        p = NotificationProvider(type="telegram", token="bot123", chat_id="-100456")
        assert p.token == "bot123"
        assert p.chat_id == "-100456"

    def test_discord_provider_fields(self):
        """Discord provider stores webhook_url."""
        p = NotificationProvider(
            type="discord", webhook_url="https://discord.com/api/webhooks/123/abc"
        )
        assert p.webhook_url == "https://discord.com/api/webhooks/123/abc"

    def test_bark_provider_fields(self):
        """Bark provider stores server_url and device_key."""
        p = NotificationProvider(
            type="bark", server_url="https://api.day.app", device_key="mykey"
        )
        assert p.server_url == "https://api.day.app"
        assert p.device_key == "mykey"

    def test_pushover_provider_fields(self):
        """Pushover provider stores user_key and api_token."""
        p = NotificationProvider(type="pushover", user_key="uk1", api_token="at1")
        assert p.user_key == "uk1"
        assert p.api_token == "at1"

    def test_url_field_property(self):
        """Webhook provider stores url."""
        p = NotificationProvider(type="webhook", url="https://example.com/hook")
        assert p.url == "https://example.com/hook"

    def test_optional_fields_default_empty_string(self):
        """Unset optional properties return empty string, not None."""
        p = NotificationProvider(type="telegram")
        assert p.token == ""
        assert p.chat_id == ""
        assert p.webhook_url == ""

    def test_provider_can_be_disabled(self):
        """Provider can be disabled without removing it."""
        p = NotificationProvider(type="telegram", enabled=False)
        assert p.enabled is False

    def test_env_var_expansion_in_token(self, monkeypatch):
        """Token field expands shell environment variables."""
        monkeypatch.setenv("TEST_BOT_TOKEN", "real-token-value")
        p = NotificationProvider(type="telegram", token="$TEST_BOT_TOKEN")
        assert p.token == "real-token-value"


# ---------------------------------------------------------------------------
# Notification model
# ---------------------------------------------------------------------------


class TestNotificationProviders:
    def test_new_format_no_migration(self):
        """New format with providers list is not touched."""
        n = NotificationConfig(
            enable=True,
            providers=[NotificationProvider(type="telegram", token="tok")],
        )
        assert len(n.providers) == 1
        assert n.providers[0].type == "telegram"

    def test_notification_empty_providers_by_default(self):
        """Default Notification has no providers."""
        n = NotificationConfig()
        assert n.providers == []
        assert n.enable is False


# ---------------------------------------------------------------------------
# Downloader env-var expansion
# ---------------------------------------------------------------------------


class TestDownloaderEnvExpansion:
    def test_host_expands_env_var(self, monkeypatch):
        """DownloaderOptions.host expands $VAR references."""
        monkeypatch.setenv("QB_HOST", "192.168.5.10:8080")
        d = DownloaderOptions(host="$QB_HOST")
        assert d.host == "192.168.5.10:8080"

    def test_username_expands_env_var(self, monkeypatch):
        """DownloaderOptions.username expands $VAR references."""
        monkeypatch.setenv("QB_USER", "myuser")
        d = DownloaderOptions(username="$QB_USER")
        assert d.username == "myuser"

    def test_password_expands_env_var(self, monkeypatch):
        """DownloaderOptions.password expands $VAR references."""
        monkeypatch.setenv("QB_PASS", "s3cret")
        d = DownloaderOptions(password="$QB_PASS")
        assert d.password == "s3cret"

    def test_literal_host_not_expanded(self):
        """Literal host strings without $ are returned as-is."""
        d = DownloaderOptions(host="localhost:8080")
        assert d.host == "localhost:8080"


# ---------------------------------------------------------------------------
# Factory defaults
# ---------------------------------------------------------------------------


class TestDefaultSettings:
    """出厂默认值来自 Config 模型本身（首次运行由 Settings.init() 写出）。"""

    def test_security_default_tokens_empty(self):
        assert Config().security.login_tokens == []
        assert Config().security.mcp_tokens == []

    def test_notification_uses_providers_format(self):
        notif = Config().model_dump()["notification"]
        assert notif["providers"] == []
        assert "type" not in notif

    def test_rss_parser_defaults_to_classic_engine(self):
        """Factory defaults preserve the pre-Preview parser behaviour."""
        assert Config().rss_parser.engine == "classic"

    def test_revision_conflict_policy_defaults_to_hold(self):
        assert Config().plugins.slots.conflict_policy == "hold"


class TestNetworkBaseUrls:
    """Configurable TMDB / bgm.tv base URLs (#1040, #1042)."""

    def test_defaults_are_official_endpoints(self):
        from module.models.config import Config

        net = Config().network
        assert net.tmdb_base_url == "https://api.themoviedb.org"
        assert net.bgm_base_url == "https://api.bgm.tv"

    def test_tmdb_url_builders_use_configured_base(self):
        import sys
        from unittest.mock import patch

        import module.parser.analyser.tmdb_parser  # noqa: F401

        tp = sys.modules["module.parser.analyser.tmdb_parser"]
        with patch.object(
            tp.settings.network, "tmdb_base_url", "https://tmdb.mirror.test/"
        ):
            assert tp.search_url("q").startswith("https://tmdb.mirror.test/3/search/tv")
            assert tp.info_url("1", "zh").startswith("https://tmdb.mirror.test/3/tv/1")

    async def test_bgm_calendar_uses_configured_base(self):
        from unittest.mock import patch

        from module.parser.analyser import bgm_calendar

        captured = {}

        class _Req:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def get_json(self, url):
                captured["url"] = url
                return None

        with (
            patch.object(
                bgm_calendar.settings.network, "bgm_base_url", "https://bgm.mirror.test"
            ),
            patch.object(bgm_calendar, "RequestContent", _Req),
        ):
            await bgm_calendar.fetch_bgm_calendar()

        assert captured["url"] == "https://bgm.mirror.test/calendar"


# ---------------------------------------------------------------------------
# Settings._migrate_old_config: 掩码哨兵清洗
# ---------------------------------------------------------------------------


class TestScrubCorruptedMasks:
    """3.2.3/3.2.4 只掩码不恢复，保存过配置的用户把字面 ******** 写进了
    密码/密钥字段（代理认证因此失败，TG 报告）。加载时按空值清洗。"""

    def test_literal_mask_in_sensitive_field_is_scrubbed(self):
        config = {
            "program": {},
            "rss_parser": {},
            "proxy": {"password": "********", "username": "u"},
            "downloader": {"password": "********"},
        }
        result = Settings._migrate_old_config(config)
        assert result["proxy"]["password"] == ""
        assert result["downloader"]["password"] == ""

    def test_real_values_and_non_sensitive_keys_are_untouched(self):
        config = {
            "program": {},
            "rss_parser": {},
            "proxy": {"password": "real-pass", "host": "********"},
        }
        result = Settings._migrate_old_config(config)
        assert result["proxy"]["password"] == "real-pass"
        assert result["proxy"]["host"] == "********"
