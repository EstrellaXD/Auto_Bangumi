"""Tests for configuration: loading, env overrides, defaults, migration."""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch

from module.models.config import (
    Config,
    Program,
    Downloader,
    RSSParser,
    BangumiManage,
    Proxy,
    Notification as NotificationConfig,
)
from module.conf.config import Settings


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
        assert "720" in config.rss_parser.filter

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
        """Notification is disabled by default."""
        config = Config()
        assert config.notification.enable is False
        assert config.notification.type == "telegram"


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

        loaded_config = Config.parse_obj(loaded)
        assert loaded_config.program.rss_time == config.program.rss_time
        assert loaded_config.downloader.type == config.downloader.type


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
