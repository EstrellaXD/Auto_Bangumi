"""Tests for configuration: loading, env overrides, defaults, migration."""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from module.conf.config import Settings
from module.conf.const import BCOLORS, DEFAULT_SETTINGS
from module.models.config import (
    Config,
    Downloader,
    NotificationProvider,
    Program,
    Proxy,
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
        assert config.bangumi_manage.rename_method == "pn"
        assert config.bangumi_manage.group_tag is False
        assert config.bangumi_manage.remove_bad_torrent is False
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


class TestConfigSerialization:
    def test_dict_uses_alias(self):
        """Config.dict() uses field aliases (by_alias=True)."""
        config = Config()
        d = config.dict()
        # Downloader uses alias 'host' not 'host_'
        assert "host" in d["downloader"]
        assert "host_" not in d["downloader"]

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
    def test_sleep_time_to_rss_time(self):
        """Migrates sleep_time → rss_time."""
        old_config = {
            "program": {"sleep_time": 1800},
            "rss_parser": {},
        }
        result = Settings._migrate_old_config(old_config)
        assert result["program"]["rss_time"] == 1800
        assert "sleep_time" not in result["program"]

    def test_times_to_rename_time(self):
        """Migrates times → rename_time."""
        old_config = {
            "program": {"times": 120},
            "rss_parser": {},
        }
        result = Settings._migrate_old_config(old_config)
        assert result["program"]["rename_time"] == 120
        assert "times" not in result["program"]

    def test_removes_data_version(self):
        """Removes deprecated data_version field."""
        old_config = {
            "program": {"data_version": 2},
            "rss_parser": {},
        }
        result = Settings._migrate_old_config(old_config)
        assert "data_version" not in result["program"]

    def test_removes_deprecated_rss_parser_fields(self):
        """Removes deprecated type, custom_url, token, enable_tmdb from rss_parser."""
        old_config = {
            "program": {},
            "rss_parser": {
                "type": "mikan",
                "custom_url": "https://custom.url",
                "token": "abc",
                "enable_tmdb": True,
                "enable": True,
            },
        }
        result = Settings._migrate_old_config(old_config)
        assert "type" not in result["rss_parser"]
        assert "custom_url" not in result["rss_parser"]
        assert "token" not in result["rss_parser"]
        assert "enable_tmdb" not in result["rss_parser"]
        assert result["rss_parser"]["enable"] is True

    def test_no_migration_needed(self):
        """Already-current config passes through unchanged."""
        current_config = {
            "program": {"rss_time": 900, "rename_time": 60},
            "rss_parser": {"enable": True},
        }
        result = Settings._migrate_old_config(current_config)
        assert result["program"]["rss_time"] == 900
        assert result["program"]["rename_time"] == 60

    def test_both_old_and_new_fields(self):
        """When both sleep_time and rss_time exist, removes sleep_time."""
        config = {
            "program": {"sleep_time": 1800, "rss_time": 900},
            "rss_parser": {},
        }
        result = Settings._migrate_old_config(config)
        assert result["program"]["rss_time"] == 900
        assert "sleep_time" not in result["program"]


class TestMigrateOpenAIToLLM:
    """experimental_openai → llm 自动迁移（provider=openai，mode=primary）。"""

    def test_old_openai_config_populates_llm_section(self):
        """旧配置有 enable/api_key 且无 llm 段时，迁移到 llm 段。"""
        old_config = {
            "program": {},
            "rss_parser": {},
            "experimental_openai": {
                "enable": True,
                "api_key": "sk-old",
                "api_base": "https://api.deepseek.com/v1",
                "model": "deepseek-chat",
            },
        }
        result = Settings._migrate_old_config(old_config)
        assert result["llm"] == {
            "enable": True,
            "provider": "openai",
            "api_key": "sk-old",
            "model": "deepseek-chat",
            "base_url": "https://api.deepseek.com/v1",
            # 旧版语义是 LLM 优先解析
            "mode": "primary",
        }
        # 旧段保留，便于降级回滚
        assert result["experimental_openai"]["api_key"] == "sk-old"

    def test_official_api_base_migrates_to_empty_base_url(self):
        """官方 API 地址迁移为空串（空串即官方 API）。"""
        old_config = {
            "program": {},
            "rss_parser": {},
            "experimental_openai": {
                "enable": True,
                "api_key": "sk-old",
                "api_base": "https://api.openai.com/v1",
            },
        }
        result = Settings._migrate_old_config(old_config)
        assert result["llm"]["base_url"] == ""

    def test_already_migrated_config_untouched(self):
        """llm 段已有有效内容时不再迁移（幂等）。"""
        migrated = {
            "program": {},
            "rss_parser": {},
            "experimental_openai": {"enable": True, "api_key": "sk-old"},
            "llm": {
                "enable": False,
                "provider": "gemini",
                "api_key": "AIza-new",
                "model": "gemini-2.5-flash",
                "base_url": "",
                "mode": "fallback",
            },
        }
        result = Settings._migrate_old_config(json.loads(json.dumps(migrated)))
        assert result["llm"] == migrated["llm"]

    def test_unconfigured_openai_section_not_migrated(self):
        """旧段未启用且无 api_key 时，不注入 llm 段（用默认值即可）。"""
        config = {
            "program": {},
            "rss_parser": {},
            "experimental_openai": {"enable": False, "api_key": ""},
        }
        result = Settings._migrate_old_config(config)
        assert "llm" not in result

    def test_migrated_defaults_fill_model(self):
        """旧段缺 model 时迁移用默认模型。"""
        config = {
            "program": {},
            "rss_parser": {},
            "experimental_openai": {"enable": True, "api_key": "sk-old"},
        }
        result = Settings._migrate_old_config(config)
        assert result["llm"]["model"] == "gpt-5-mini"
        assert result["llm"]["mode"] == "primary"


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
        assert "downloader" in data
        # 新配置文件包含 llm 段（旧 experimental_openai 段同样保留）
        assert "llm" in data
        assert data["rss_parser"]["engine"] == "classic"

    def test_load_old_openai_config_migrates_to_llm(self, tmp_path):
        """加载含旧 experimental_openai 的文件后，llm 段生效且为 primary 模式。"""
        config_data = Config().dict()
        del config_data["llm"]
        config_data["experimental_openai"].update(
            {"enable": True, "api_key": "sk-old", "model": "gpt-4o"}
        )
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        with patch("module.conf.config.CONFIG_PATH", config_file):
            s = Settings.__new__(Settings)
            Config.__init__(s)
            s.load()

        assert s.llm.enable is True
        assert s.llm.provider == "openai"
        assert s.llm.api_key == "sk-old"
        assert s.llm.model == "gpt-4o"
        assert s.llm.mode == "primary"


# ---------------------------------------------------------------------------
# Environment variable overrides
# ---------------------------------------------------------------------------


class TestEnvOverrides:
    def test_downloader_host_from_env(self, tmp_path):
        """AB_DOWNLOADER_HOST env var overrides downloader host."""
        config_file = tmp_path / "config.json"

        env = {"AB_DOWNLOADER_HOST": "192.168.1.100:9090"}
        with patch.dict(os.environ, env, clear=False):
            with patch("module.conf.config.CONFIG_PATH", config_file):
                s = Settings.__new__(Settings)
                Config.__init__(s)
                s.init()

        assert "192.168.1.100:9090" in s.downloader.host

    def test_rss_parser_engine_from_env(self, tmp_path):
        """AB_RSS_PARSER_ENGINE selects a supported parser engine."""
        config_file = tmp_path / "config.json"

        with patch.dict(os.environ, {"AB_RSS_PARSER_ENGINE": "TOKENIZER"}, clear=False):
            with patch("module.conf.config.CONFIG_PATH", config_file):
                s = Settings.__new__(Settings)
                Config.__init__(s)
                s.init()

        assert s.rss_parser.engine == "tokenizer"


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
# Notification model - legacy migration
# ---------------------------------------------------------------------------


class TestNotificationLegacyMigration:
    def test_new_format_no_migration(self):
        """New format with providers list is not touched."""
        n = NotificationConfig(
            enable=True,
            providers=[NotificationProvider(type="telegram", token="tok")],
        )
        assert len(n.providers) == 1
        assert n.providers[0].type == "telegram"

    def test_old_format_migrates_to_provider(self):
        """Old single-provider fields (type, token, chat_id) migrate to providers list."""
        n = NotificationConfig(
            enable=True,
            type="telegram",
            token="bot_token",
            chat_id="-100123",
        )
        assert len(n.providers) == 1
        provider = n.providers[0]
        assert provider.type == "telegram"
        assert provider.enabled is True

    def test_old_format_no_migration_when_providers_already_set(self):
        """When providers already exist, legacy fields do not create additional providers."""
        n = NotificationConfig(
            enable=True,
            type="telegram",
            token="unused",
            providers=[
                NotificationProvider(type="discord", webhook_url="https://d.co")
            ],
        )
        assert len(n.providers) == 1
        assert n.providers[0].type == "discord"

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
        """Downloader.host expands $VAR references."""
        monkeypatch.setenv("QB_HOST", "192.168.5.10:8080")
        d = Downloader(host="$QB_HOST")
        assert d.host == "192.168.5.10:8080"

    def test_username_expands_env_var(self, monkeypatch):
        """Downloader.username expands $VAR references."""
        monkeypatch.setenv("QB_USER", "myuser")
        d = Downloader(username="$QB_USER")
        assert d.username == "myuser"

    def test_password_expands_env_var(self, monkeypatch):
        """Downloader.password expands $VAR references."""
        monkeypatch.setenv("QB_PASS", "s3cret")
        d = Downloader(password="$QB_PASS")
        assert d.password == "s3cret"

    def test_literal_host_not_expanded(self):
        """Literal host strings without $ are returned as-is."""
        d = Downloader(host="localhost:8080")
        assert d.host == "localhost:8080"


# ---------------------------------------------------------------------------
# DEFAULT_SETTINGS structure
# ---------------------------------------------------------------------------


class TestDefaultSettings:
    def test_security_section_present(self):
        """DEFAULT_SETTINGS contains a security section."""
        assert "security" in DEFAULT_SETTINGS

    def test_security_default_mcp_whitelist(self):
        """Default MCP whitelist contains private network ranges."""
        mcp_wl = DEFAULT_SETTINGS["security"]["mcp_whitelist"]
        assert "127.0.0.0/8" in mcp_wl
        assert "192.168.0.0/16" in mcp_wl
        assert "10.0.0.0/8" in mcp_wl

    def test_security_default_tokens_empty(self):
        """Default security token lists are empty."""
        assert DEFAULT_SETTINGS["security"]["login_tokens"] == []
        assert DEFAULT_SETTINGS["security"]["mcp_tokens"] == []

    def test_notification_uses_providers_format(self):
        """DEFAULT_SETTINGS notification uses new providers format."""
        notif = DEFAULT_SETTINGS["notification"]
        assert "providers" in notif
        assert notif["providers"] == []
        assert "type" not in notif

    def test_rss_parser_defaults_to_classic_engine(self):
        """Factory defaults preserve the pre-Preview parser behaviour."""
        assert DEFAULT_SETTINGS["rss_parser"]["engine"] == "classic"


# ---------------------------------------------------------------------------
# BCOLORS utility
# ---------------------------------------------------------------------------


class TestBCOLORS:
    def test_wrap_single_string(self):
        """BCOLORS._() wraps a string with color codes and reset."""
        result = BCOLORS._(BCOLORS.OKGREEN, "hello")
        assert "hello" in result
        assert BCOLORS.OKGREEN in result
        assert BCOLORS.ENDC in result

    def test_wrap_multiple_strings(self):
        """BCOLORS._() joins multiple args with commas."""
        result = BCOLORS._(BCOLORS.WARNING, "foo", "bar")
        assert "foo" in result
        assert "bar" in result

    def test_wrap_non_string_arg(self):
        """BCOLORS._() converts non-string args to str."""
        result = BCOLORS._(BCOLORS.FAIL, 42)
        assert "42" in result

    def test_all_color_constants_are_strings(self):
        """All BCOLORS constants are strings."""
        for attr in [
            "HEADER",
            "OKBLUE",
            "OKCYAN",
            "OKGREEN",
            "WARNING",
            "FAIL",
            "ENDC",
        ]:
            assert isinstance(getattr(BCOLORS, attr), str)


# ---------------------------------------------------------------------------
# Migration: security section injection
# ---------------------------------------------------------------------------


class TestMigrateSecuritySection:
    def test_adds_security_when_missing(self):
        """_migrate_old_config injects a default security section when absent."""
        old_config: dict = {
            "program": {},
            "rss_parser": {},
        }
        result = Settings._migrate_old_config(old_config)
        assert "security" in result
        assert "mcp_whitelist" in result["security"]

    def test_preserves_existing_security_section(self):
        """_migrate_old_config does not overwrite an existing security section."""
        existing_config = {
            "program": {},
            "rss_parser": {},
            "security": {
                "login_whitelist": ["10.0.0.0/8"],
                "login_tokens": ["mytoken"],
                "mcp_whitelist": [],
                "mcp_tokens": [],
            },
        }
        result = Settings._migrate_old_config(existing_config)
        assert result["security"]["login_tokens"] == ["mytoken"]
        assert result["security"]["login_whitelist"] == ["10.0.0.0/8"]


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
        from unittest.mock import AsyncMock, patch

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
