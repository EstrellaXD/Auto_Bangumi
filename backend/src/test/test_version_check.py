"""version_check：记录运行版本，并拒绝从 3.3 以前的版本直接升级。"""

import importlib

import pytest

vc = importlib.import_module("module.update.version_check")


@pytest.fixture
def paths(tmp_path, monkeypatch):
    version_path = tmp_path / "version.info"
    legacy_path = tmp_path / "data.json"
    monkeypatch.setattr(vc, "VERSION_PATH", version_path)
    monkeypatch.setattr(vc, "LEGACY_DATA_PATH", legacy_path)
    monkeypatch.setattr(vc, "VERSION", "4.0.0")
    return version_path, legacy_path


def test_missing_version_file_records_current(paths):
    version_path, _ = paths
    assert vc.version_check() is None
    assert version_path.read_text() == "4.0.0\n"


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
    with pytest.raises(vc.UnsupportedUpgradeError, match=previous):
        vc.version_check()
    # 拒绝时不改写记录，用户回退到 3.3.x 后仍能正常迁移
    assert version_path.read_text() == previous + "\n"


def test_legacy_data_json_is_refused(paths):
    _, legacy_path = paths
    legacy_path.write_text("{}")
    with pytest.raises(vc.UnsupportedUpgradeError, match="2.x"):
        vc.version_check()


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
