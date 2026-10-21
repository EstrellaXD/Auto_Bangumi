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


def test_on_event_organized_passes_env_and_placeholders_without_shell(tmp_path):
    out = tmp_path / "out.json"
    command = [sys.executable, "-c", DUMP, str(out), "{torrent_hash}", "$HOME; {x}"]
    run({"command": command})
    got = json.loads(out.read_text())
    # $HOME 与 ; 按字面传入：没有经过 shell；未知占位符原样保留
    assert got["argv"] == ["abc", "$HOME; {x}"]
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


def test_on_event_nonzero_exit_logs_code_and_stderr(caplog):
    script = "import sys; sys.stderr.write('boom'); sys.exit(3)"
    with caplog.at_level(logging.WARNING):
        run({"command": [sys.executable, "-c", script]})
    assert "退出码 3" in caplog.text and "boom" in caplog.text


def test_on_event_missing_program_is_logged_not_raised(caplog):
    with caplog.at_level(logging.WARNING):
        run({"command": ["/nonexistent/ab-run-command-test"]})
    assert "无法启动命令" in caplog.text
