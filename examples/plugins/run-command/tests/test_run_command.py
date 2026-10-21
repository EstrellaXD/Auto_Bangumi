import asyncio
import json
import logging
import sys
import time

import pytest
from run_command import RunCommand

from ab_sdk.events import FileRenamed, OrganizedFile, TorrentOrganized
from ab_sdk.testing import create_plugin

ORGANIZED = TorrentOrganized(
    torrent_hash="abc",
    bangumi_id=None,
    files=(
        OrganizedFile("/dl/Show/Season 1/Show S01E01.mkv", "media"),
        OrganizedFile("/dl/Show/Season 1/Show S01E01.ass", "subtitle"),
    ),
)
RENAMED = FileRenamed(
    bangumi_id=7, old_path="/dl/a.mkv", new_path="/dl/b.mkv", file_kind="media"
)

# 子进程把收到的参数与 AB_* 环境变量写进 argv[1] 指定的文件
DUMP = (
    "import json, os, sys; "
    "json.dump({'argv': sys.argv[2:], "
    "'env': {k: v for k, v in os.environ.items() if k.startswith('AB_')}}, "
    "open(sys.argv[1], 'w'))"
)


def run(options: dict, event=ORGANIZED) -> None:
    plugin, _ = create_plugin(RunCommand, options)
    asyncio.run(plugin.on_event(event))


def test_on_event_organized_passes_env_and_placeholders_without_shell(
    tmp_path, monkeypatch
):
    # 宿主自己的 AB_* 凭据不传给命令
    monkeypatch.setenv("AB_DOWNLOADER_PASSWORD", "s3cret")
    out = tmp_path / "out.json"
    command = [
        *(sys.executable, "-c", DUMP, str(out)),
        *("{torrent_hash}", "$HOME; {x}", "pre-{torrent_hash}", "{files}"),
    ]
    run({"command": command})
    got = json.loads(out.read_text())
    # $HOME 与 ; 按字面传入：没有经过 shell；未知占位符与夹在参数里的占位符原样保留；
    # {files} 展开为每个文件一个参数
    assert got["argv"] == [
        "abc",
        "$HOME; {x}",
        "pre-{torrent_hash}",
        "/dl/Show/Season 1/Show S01E01.mkv",
        "/dl/Show/Season 1/Show S01E01.ass",
    ]
    assert got["env"] == {
        "AB_EVENT": "torrent.organized",
        "AB_BANGUMI_ID": "",
        "AB_DOWNLOADER_ID": "default",
        "AB_TORRENT_HASH": "abc",
        "AB_FILES": "/dl/Show/Season 1/Show S01E01.mkv\n"
        "/dl/Show/Season 1/Show S01E01.ass",
    }


def test_on_event_renamed_when_selected_passes_rename_fields(tmp_path):
    out = tmp_path / "out.json"
    command = [sys.executable, "-c", DUMP, str(out), "{old_path}"]
    run({"command": command, "events": ["file.renamed"]}, RENAMED)
    got = json.loads(out.read_text())
    assert got["argv"] == ["/dl/a.mkv"]
    assert got["env"]["AB_BANGUMI_ID"] == "7"
    assert got["env"]["AB_NEW_PATH"] == "/dl/b.mkv"
    assert got["env"]["AB_FILE_KIND"] == "media"


@pytest.mark.parametrize(
    ("options", "event"),
    [({"command": []}, ORGANIZED), ({}, RENAMED)],
)
def test_on_event_unwanted_runs_nothing(tmp_path, options, event):
    out = tmp_path / "out.json"
    options.setdefault("command", [sys.executable, "-c", DUMP, str(out)])
    run(options, event)
    assert not out.exists()


def test_on_event_timeout_kills_command(caplog):
    command = [sys.executable, "-c", "import time; time.sleep(30)"]
    plugin, _ = create_plugin(RunCommand, {"command": command, "timeout": 1})
    start = time.monotonic()
    with caplog.at_level(logging.WARNING):
        asyncio.run(plugin.on_event(ORGANIZED))
    assert time.monotonic() - start < 10
    assert "已终止" in caplog.text


def test_on_event_background_child_does_not_delay_success(caplog):
    # 后台进程继承了 stderr；命令本身已退出，不应等到后台进程结束
    command = ["sh", "-c", "sleep 5 & exit 0"]
    plugin, _ = create_plugin(RunCommand, {"command": command, "timeout": 2})
    start = time.monotonic()
    with caplog.at_level(logging.INFO):
        asyncio.run(plugin.on_event(ORGANIZED))
    assert time.monotonic() - start < 2
    assert "已完成" in caplog.text and "已终止" not in caplog.text


def test_on_event_files_placeholder_keeps_newline_in_path(tmp_path):
    # {files} 取原始路径列表：含换行的路径仍是一个参数（AB_FILES 只能按行拼接）
    out = tmp_path / "out.json"
    event = TorrentOrganized(
        torrent_hash="abc",
        bangumi_id=1,
        files=(OrganizedFile("/dl/a\nb.mkv", "media"),),
    )
    run({"command": [sys.executable, "-c", DUMP, str(out), "{files}"]}, event)
    assert json.loads(out.read_text())["argv"] == ["/dl/a\nb.mkv"]


def test_on_event_huge_stderr_keeps_only_tail(caplog):
    # 输出远超管道缓冲：边读边丢，命令不会卡到超时，日志只带最后 2000 字节
    script = (
        "import sys; sys.stderr.write('x' * 5_000_000 + 'END'); sys.stderr.flush(); "
        "sys.exit(3)"
    )
    start = time.monotonic()
    with caplog.at_level(logging.WARNING):
        run({"command": [sys.executable, "-c", script], "timeout": 10})
    assert time.monotonic() - start < 5
    [record] = caplog.records
    assert "退出码 3" in record.getMessage()
    assert record.args[-1] == "x" * 1997 + "END"


def test_on_event_nonzero_exit_logs_code_and_stderr(caplog):
    script = "import sys; sys.stderr.write('boom'); sys.exit(3)"
    with caplog.at_level(logging.WARNING):
        run({"command": [sys.executable, "-c", script]})
    assert "退出码 3" in caplog.text and "boom" in caplog.text


def test_on_event_missing_program_is_logged_not_raised(caplog):
    with caplog.at_level(logging.WARNING):
        run({"command": ["/nonexistent/ab-run-command-test"]})
    assert "无法启动命令" in caplog.text
