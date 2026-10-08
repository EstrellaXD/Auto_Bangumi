"""ab-plugin 命令行：脚手架、校验、打包与 dev 链接。"""

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from ab_sdk.cli import KINDS, main


def _new(tmp_path: Path, kind: str = "rename", plugin_id: str = "my-plugin") -> Path:
    assert main(["new", plugin_id, "--kind", kind, "--dir", str(tmp_path)]) == 0
    return tmp_path / plugin_id


@pytest.mark.parametrize("kind", KINDS)
def test_new_scaffold_passes_validate_and_its_own_contract_tests(tmp_path, kind):
    plugin_dir = _new(tmp_path, kind)

    assert main(["validate", str(plugin_dir)]) == 0
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=plugin_dir,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_new_existing_target_refused(tmp_path):
    _new(tmp_path)

    assert main(["new", "my-plugin", "--dir", str(tmp_path)]) == 1


def test_new_invalid_id_refused(tmp_path):
    assert main(["new", "My_Plugin", "--dir", str(tmp_path)]) == 1


def _break(plugin_dir: Path, problem: str) -> None:
    manifest = plugin_dir / "plugin.toml"
    if problem == "sdk":
        manifest.write_text(
            manifest.read_text().replace('sdk = ">=0.5,<1"', 'sdk = ">=9"')
        )
    elif problem == "entry":
        (plugin_dir / "my_plugin" / "__init__.py").unlink()
    elif problem == "native":
        (plugin_dir / "my_plugin" / "speed.so").write_bytes(b"")
    elif problem == "ui":
        manifest.write_text(
            manifest.read_text()
            + '\n[[plugin.ui]]\nslot = "page"\nelement = "ab-plugin-my-plugin"\n'
            'entry = "web/index.js"\ntitle = { en-US = "X" }\n'
        )
    elif problem == "syntax":
        manifest.write_text("[plugin\n")


@pytest.mark.parametrize("problem", ["sdk", "entry", "native", "ui", "syntax"])
def test_validate_broken_plugin_fails(tmp_path, capsys, problem):
    plugin_dir = _new(tmp_path)
    _break(plugin_dir, problem)

    assert main(["validate", str(plugin_dir)]) == 1
    assert "错误" in capsys.readouterr().err


@pytest.mark.parametrize("tooling_dir", [".venv", "node_modules", ".mypy_cache"])
def test_validate_ignores_native_files_in_tooling_dirs(tmp_path, tooling_dir):
    plugin_dir = _new(tmp_path)
    native = plugin_dir / tooling_dir / "lib" / "_core.so"
    native.parent.mkdir(parents=True)
    native.write_bytes(b"")

    assert main(["validate", str(plugin_dir)]) == 0


def test_fingerprint_ignores_tooling_dirs(tmp_path):
    from module.plugin.manager import _fingerprint

    plugin_dir = _new(tmp_path)
    before = _fingerprint(plugin_dir)
    (plugin_dir / ".venv").mkdir()
    (plugin_dir / ".venv" / "x.py").write_text("x")

    assert _fingerprint(plugin_dir) == before


def test_pack_puts_contents_at_zip_root_and_is_reproducible(tmp_path):
    plugin_dir = _new(tmp_path)
    (plugin_dir / "my_plugin" / "__pycache__").mkdir()
    (plugin_dir / "my_plugin" / "__pycache__" / "x.pyc").write_bytes(b"")

    assert main(["pack", str(plugin_dir), "-o", str(tmp_path / "out1")]) == 0
    assert main(["pack", str(plugin_dir), "-o", str(tmp_path / "out2")]) == 0

    first = tmp_path / "out1" / "my-plugin-0.1.0.zip"
    with zipfile.ZipFile(first) as zf:
        # 测试、工程文件与缓存不进包
        assert zf.namelist() == [
            "README.md",
            "my_plugin/__init__.py",
            "plugin.toml",
        ]
    assert first.read_bytes() == (tmp_path / "out2" / first.name).read_bytes()


def test_pack_refuses_invalid_plugin(tmp_path):
    plugin_dir = _new(tmp_path)
    _break(plugin_dir, "entry")

    assert main(["pack", str(plugin_dir), "-o", str(tmp_path / "out")]) == 1
    assert not (tmp_path / "out").exists()


@pytest.fixture
def config_dir(tmp_path):
    path = tmp_path / "host" / "config"
    path.mkdir(parents=True)
    (path / "config_dev.json").write_text(json.dumps({"program": {"rss_time": 900}}))
    return path


def test_dev_links_plugin_and_enables_dev_mode(tmp_path, config_dir):
    plugin_dir = _new(tmp_path)

    assert main(["dev", str(plugin_dir), "--config-dir", str(config_dir)]) == 0
    # 再次运行是幂等的
    assert main(["dev", str(plugin_dir), "--config-dir", str(config_dir)]) == 0

    link = config_dir / "plugins" / "local" / "my-plugin"
    assert link.is_symlink() and link.resolve() == plugin_dir.resolve()
    config = json.loads((config_dir / "config_dev.json").read_text())
    assert config["program"] == {"rss_time": 900}
    assert config["plugins"] == {
        "dev_mode": True,
        "allow_unsigned": True,
        "enabled": {"my-plugin": True},
    }


def test_dev_refuses_when_id_is_linked_elsewhere(tmp_path, config_dir):
    first = _new(tmp_path / "a")
    second = _new(tmp_path / "b")
    assert main(["dev", str(first), "--config-dir", str(config_dir)]) == 0

    assert main(["dev", str(second), "--config-dir", str(config_dir)]) == 1


def test_dev_without_host_config_fails(tmp_path):
    plugin_dir = _new(tmp_path)

    assert main(["dev", str(plugin_dir), "--config-dir", str(tmp_path / "none")]) == 1
