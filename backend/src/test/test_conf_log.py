"""启动时日志轮转（rotate_boot_log）：历史进备份而非被删除。"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from module.conf import log as conf_log


@pytest.fixture
def log_path(tmp_path: Path, monkeypatch) -> Path:
    path = tmp_path / "log.txt"
    monkeypatch.setattr(conf_log, "LOG_PATH", path)
    return path


class TestRotateBootLog:
    def test_rotate_shifts_current_log_to_backup(self, log_path: Path):
        log_path.write_text("previous boot")

        conf_log.rotate_boot_log()

        assert not log_path.exists()
        assert log_path.with_name("log.txt.1").read_text() == "previous boot"

    def test_rotate_shifts_backup_chain(self, log_path: Path):
        log_path.write_text("boot 3")
        log_path.with_name("log.txt.1").write_text("boot 2")
        log_path.with_name("log.txt.2").write_text("boot 1")

        conf_log.rotate_boot_log()

        assert log_path.with_name("log.txt.1").read_text() == "boot 3"
        assert log_path.with_name("log.txt.2").read_text() == "boot 2"
        assert log_path.with_name("log.txt.3").read_text() == "boot 1"

    def test_rotate_drops_oldest_beyond_backup_count(self, log_path: Path):
        log_path.write_text("new")
        for i in (1, 2, 3):
            log_path.with_name(f"log.txt.{i}").write_text(f"old {i}")

        conf_log.rotate_boot_log()

        # 备份数量固定：最老的一份被淘汰
        assert log_path.with_name("log.txt.3").read_text() == "old 2"
        assert log_path.with_name("log.txt.1").read_text() == "new"

    def test_rotate_noop_on_missing_log(self, log_path: Path):
        conf_log.rotate_boot_log()
        assert not log_path.with_name("log.txt.1").exists()

    def test_rotate_noop_on_empty_log(self, log_path: Path):
        log_path.write_text("")
        conf_log.rotate_boot_log()
        assert not log_path.with_name("log.txt.1").exists()

    def test_rotate_swallows_os_errors(self, log_path: Path, monkeypatch):
        """轮转失败（如卷上遗留 root 属主的备份）不能阻断启动。"""
        log_path.write_text("content")

        def boom(self):
            raise OSError("permission denied")

        monkeypatch.setattr("logging.handlers.RotatingFileHandler.doRollover", boom)

        conf_log.rotate_boot_log()

        assert log_path.read_text() == "content"


def test_setup_logger_replaces_handlers_installed_by_earlier_imports(tmp_path: Path):
    """生产导入顺序里 mcp 早于 setup_logger 导入；根日志器已有处理器时
    basicConfig 不能被静默跳过，日志必须落到 data/log.txt。"""
    code = (
        "import logging, main\n"
        "assert [type(h).__name__ for h in logging.getLogger().handlers]"
        " == ['QueueHandler']\n"
        "logging.getLogger('probe').info('probe-marker')\n"
    )
    src = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(src)}
    subprocess.run(
        [sys.executable, "-c", code], cwd=tmp_path, env=env, check=True, timeout=60
    )
    # 子进程退出时 atexit 会排空日志队列
    assert "probe-marker" in (tmp_path / "data" / "log.txt").read_text()
