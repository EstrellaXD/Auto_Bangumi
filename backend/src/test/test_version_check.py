"""version_check：记录运行版本，并拒绝从 3.3 以前的版本直接升级。"""

import importlib
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

vc = importlib.import_module("module.update.version_check")


def _make_db(path, *tables: str) -> None:
    with closing(sqlite3.connect(path)) as conn:
        for table in tables:
            conn.execute(f"CREATE TABLE {table} (id INTEGER)")


@pytest.fixture
def paths(tmp_path, monkeypatch):
    version_path = tmp_path / "version.info"
    legacy_path = tmp_path / "data.json"
    db_path = tmp_path / "data.db"
    _make_db(db_path, "bangumi", "rssitem")
    monkeypatch.setattr(vc, "VERSION_PATH", version_path)
    monkeypatch.setattr(vc, "LEGACY_DATA_PATH", legacy_path)
    monkeypatch.setattr(vc, "DATABASE_PATH", db_path)
    monkeypatch.setattr(vc, "VERSION", "4.0.0")
    # 发布版本的配置文件（测试环境是 config_dev.json）
    monkeypatch.setattr(vc, "CONFIG_PATH", Path("config/config.json"))
    return version_path, legacy_path


def test_missing_version_file_records_current(paths):
    version_path, _ = paths
    assert vc.version_check() is None
    assert version_path.read_text() == "4.0.0\n"


def test_missing_version_file_with_30_database_is_refused(paths, tmp_path, monkeypatch):
    """3.0.x 不写 version.info，数据库也没有 3.1 起才有的 rssitem 表。"""
    version_path, _ = paths
    db_path = tmp_path / "v30.db"
    _make_db(db_path, "bangumi", "torrent", "user")
    monkeypatch.setattr(vc, "DATABASE_PATH", db_path)
    # 只有 3.1.x 会在缺少 version.info 时补跑 3.0 → 3.1 的数据迁移
    with pytest.raises(vc.UnsupportedUpgradeError, match=r"3\.0.*3\.1\.x"):
        vc.version_check()
    assert not version_path.exists()


def test_upgrade_from_33_is_recorded(paths):
    version_path, _ = paths
    version_path.write_text("3.2.7\n3.3.6\n")
    last = vc.version_check()
    assert str(last) == "3.3.6"
    assert version_path.read_text().splitlines()[-1] == "4.0.0"


def test_upgrade_from_33_prerelease_is_allowed(paths):
    version_path, _ = paths
    version_path.write_text("3.3.0-beta.2\n")
    assert str(vc.version_check()) == "3.3.0-beta.2"


def test_same_version_is_not_duplicated(paths):
    version_path, _ = paths
    version_path.write_text("4.0.0\n")
    vc.version_check()
    assert version_path.read_text() == "4.0.0\n"


def test_downgrade_is_not_recorded(paths):
    version_path, _ = paths
    version_path.write_text("4.1.0\n")
    vc.version_check()
    assert version_path.read_text() == "4.1.0\n"


@pytest.mark.parametrize("previous", ["3.2.7", "3.1.0", "2.6.4"])
def test_upgrade_from_pre_33_is_refused(paths, previous):
    version_path, _ = paths
    version_path.write_text(previous + "\n")
    with pytest.raises(vc.UnsupportedUpgradeError, match=previous) as exc:
        vc.version_check()
    # 本次启动已把 config.json 改写为 4.0 格式，提示要先还原备份再回到旧版本
    assert "config.json.v3.bak" in str(exc.value)
    # 拒绝时不改写记录，用户回退到 3.3.x 后仍能正常迁移
    assert version_path.read_text() == previous + "\n"


def test_legacy_data_json_is_refused(paths):
    _, legacy_path = paths
    legacy_path.write_text("{}")
    with pytest.raises(vc.UnsupportedUpgradeError, match="2.x"):
        vc.refuse_legacy_data()


def test_malformed_version_file_is_rewritten(paths):
    version_path, _ = paths
    version_path.write_text("garbage\n")
    assert vc.version_check() is None
    assert version_path.read_text() == "4.0.0\n"


@pytest.mark.parametrize("dev_version", ["DEV_VERSION", "local"])
def test_dev_builds_skip_the_gate(paths, monkeypatch, dev_version):
    version_path, _ = paths
    monkeypatch.setattr(vc, "VERSION", dev_version)
    version_path.write_text("3.1.0\n")
    assert vc.version_check() is None
