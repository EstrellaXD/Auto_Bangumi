"""3.3 → 4.0 配置迁移（module.update.v4）。"""

import json
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from module.conf.config import Settings
from module.models.config import DownloaderInstance
from module.update.v4 import ConfigMigrationError, migrate_v3_config, migrate_v3_dict

FIXTURE = Path(__file__).parent / "fixtures" / "config_v3.3.json"


@pytest.fixture
def v3_config(tmp_path: Path) -> Path:
    path = tmp_path / "config.json"
    shutil.copy(FIXTURE, path)
    return path


def test_settings_v33_config_round_trip_migrated(v3_config, monkeypatch):
    monkeypatch.setenv("QB_HOST", "nas:8080")
    with patch("module.conf.config.CONFIG_PATH", v3_config):
        settings = Settings()

    assert settings.downloader == DownloaderInstance(
        id="default",
        type="qbittorrent",
        host="nas:8080",
        username="ab",
        password="qb-secret",
        path="/media/downloads/Bangumi",
        ssl=True,
    )
    assert settings.plugins.slots.downloader == "default"
    assert settings.plugins.slots.rename_strategy == "advance"
    assert settings.plugins.slots.conflict_policy == "replace"
    # 其它字段原样保留
    assert settings.program.rss_time == 1800
    assert settings.bangumi_manage.group_tag is True
    assert settings.notification.providers[0].token == "tg-token"

    saved = json.loads(v3_config.read_text())
    assert "downloader" not in saved
    assert "rename_method" not in saved["bangumi_manage"]
    assert "revision_conflict_policy" not in saved["bangumi_manage"]
    # $VAR 引用原样保存，读取时才展开
    assert saved["plugins"]["instances"][0]["options"]["host"] == "$QB_HOST"
    backup = v3_config.with_name("config.json.v3.bak")
    assert backup.read_bytes() == FIXTURE.read_bytes()


def test_migrate_v3_config_second_run_noop(v3_config):
    assert migrate_v3_config(v3_config) is True
    backup = v3_config.with_name("config.json.v3.bak")
    migrated, backed_up = v3_config.read_bytes(), backup.read_bytes()

    assert migrate_v3_config(v3_config) is False
    assert v3_config.read_bytes() == migrated
    assert backup.read_bytes() == backed_up == FIXTURE.read_bytes()


def test_migrate_v4_config_untouched_without_backup(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"program": {"rss_time": 600}}))

    assert migrate_v3_config(path) is False
    assert not path.with_name("config.json.v3.bak").exists()


@pytest.mark.parametrize(
    ("section", "key", "value", "field"),
    [
        ("downloader", "ssl", "sometimes", "ssl"),
        ("bangumi_manage", "rename_method", 5, "plugins.slots.rename_strategy"),
    ],
)
def test_migrate_v3_config_invalid_field_restores_and_refuses(
    v3_config, section, key, value, field
):
    config = json.loads(v3_config.read_text())
    config[section][key] = value
    original = json.dumps(config, indent=4)
    v3_config.write_text(original)

    with pytest.raises(ConfigMigrationError, match=field):
        migrate_v3_config(v3_config)

    assert v3_config.read_text() == original
    assert v3_config.with_name("config.json.v3.bak").read_text() == original
    assert not v3_config.with_name("config.json.tmp").exists()


@pytest.mark.parametrize(
    ("method", "expected"),
    [("normal", "none"), ("none", "none"), ("pn", "pn"), ("template", "template")],
)
def test_migrate_v3_dict_rename_method_moves_to_slot(method, expected):
    config: dict[str, Any] = {"bangumi_manage": {"rename_method": method}}

    assert migrate_v3_dict(config) == ["bangumi_manage.rename_method"]
    assert config["plugins"]["slots"] == {"rename_strategy": expected}
    assert config["bangumi_manage"] == {}


def test_migrate_v3_dict_downloader_merges_into_existing_default_instance():
    config: dict[str, Any] = {
        "downloader": {"host": "qb:8080"},
        "plugins": {
            "instances": [
                {
                    "id": "default",
                    "point": "downloader",
                    "provider": "aria2",
                    "options": {"host": "old", "path": "/dl"},
                }
            ]
        },
    }

    migrate_v3_dict(config)

    assert config["plugins"]["instances"] == [
        {
            "id": "default",
            "point": "downloader",
            "provider": "aria2",
            "options": {"host": "qb:8080", "path": "/dl"},
        }
    ]
    assert config["plugins"]["slots"] == {"downloader": "default"}


def test_migrate_v3_config_existing_backup_kept_new_backup_beside_it(v3_config):
    """降级回 3.3 再升级：第一次迁移留下的备份（含真实凭据）不能被覆盖。"""
    first = v3_config.with_name("config.json.v3.bak")
    first.write_text("original 3.3 config")

    assert migrate_v3_config(v3_config) is True

    assert first.read_text() == "original 3.3 config"
    second = v3_config.with_name("config.json.v3.bak.1")
    assert second.read_bytes() == FIXTURE.read_bytes()


@pytest.mark.parametrize(
    "provider, expected",
    [
        # Bark 旧版把 device key 放在 token
        ({"type": "bark", "token": "k"}, {"type": "bark", "device_key": "k"}),
        (
            {"type": "bark", "token": "old", "device_key": "new"},
            {"type": "bark", "device_key": "new"},
        ),
        # WeCom 旧版把 webhook 地址放在 chat_id
        (
            {"type": "wecom", "chat_id": "https://hook", "token": "key"},
            {"type": "wecom", "webhook_url": "https://hook", "token": "key"},
        ),
        (
            {"type": "WeCom", "chat_id": "old", "webhook_url": "new"},
            {"type": "WeCom", "webhook_url": "new"},
        ),
    ],
)
def test_migrate_v3_dict_moves_legacy_notification_aliases(provider, expected):
    config: dict[str, Any] = {"notification": {"providers": [provider]}}

    moved = migrate_v3_dict(config)

    assert config["notification"]["providers"] == [expected]
    assert len(moved) == 1 and moved[0].startswith("notification.providers[0].")
    # 只动通知渠道：没有顺带创建 plugins 段
    assert "plugins" not in config


def test_migrate_v3_dict_keeps_other_providers_token_and_chat_id():
    telegram = {"type": "telegram", "token": "t", "chat_id": "1"}
    config: dict[str, Any] = {"notification": {"providers": [dict(telegram)]}}

    assert migrate_v3_dict(config) == []
    assert config["notification"]["providers"] == [telegram]


def test_migrate_v3_config_rewrites_file_with_legacy_bark_token(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"notification": {"providers": [{"type": "bark", "token": "k"}]}})
    )

    assert migrate_v3_config(path) is True

    saved = json.loads(path.read_text())
    assert saved["notification"]["providers"] == [{"type": "bark", "device_key": "k"}]
    assert path.with_name("config.json.v3.bak").exists()


@pytest.mark.parametrize(
    "provider",
    [
        # Settings.save() 总是把渠道的旧字段以 null 写回，不能当作 3.3 配置
        {"type": "bark", "token": None, "device_key": "k"},
        {"type": "wecom", "chat_id": None, "webhook_url": "https://hook"},
        {"type": "bark", "token": "", "device_key": ""},
    ],
)
def test_migrate_v3_config_empty_legacy_alias_is_noop(tmp_path, provider):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"notification": {"providers": [provider]}}))
    before = path.read_bytes()

    assert migrate_v3_config(path) is False

    assert path.read_bytes() == before
    assert list(tmp_path.glob("config.json.v3.bak*")) == []
