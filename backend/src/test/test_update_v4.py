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
