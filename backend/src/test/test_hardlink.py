"""内置插件 hardlink：订阅 torrent.organized，把整理好的文件链接到媒体库。"""

import asyncio
import errno
import os
import shutil
import threading
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from ab_sdk.events import OrganizedFile, TorrentOrganized
from ab_sdk.testing import create_plugin
from module.plugin.loader import BUILTIN_ROOT, discover

SEASON = "Bangumi/Anime (2024)/Season 1"


def load_candidate():
    candidates, errors = discover(
        local_root=BUILTIN_ROOT / "__missing__", entry_point_group="ab-test-none"
    )
    assert errors == []
    return {c.manifest.id: c for c in candidates}["hardlink"]


@pytest.fixture
def roots(tmp_path) -> tuple[Path, Path]:
    downloads, library = tmp_path / "downloads", tmp_path / "library"
    (downloads / SEASON).mkdir(parents=True)
    return downloads, library


def make_plugin(roots: tuple[Path, Path], **options):
    downloads, library = roots
    options = {
        "path_map": [{"from": "/dl", "to": str(downloads)}],
        "source_root": str(downloads),
        "library_root": str(library),
        **options,
    }
    return create_plugin(load_candidate().load(), options, plugin_id="hardlink")


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def organized(*names: str, downloader: str = "default") -> TorrentOrganized:
    return TorrentOrganized(
        torrent_hash="h1",
        bangumi_id=7,
        files=tuple(OrganizedFile(f"/dl/{SEASON}/{n}", "media") for n in names),
        downloader_id=downloader,
    )


def exdev(src, dst):
    raise OSError(errno.EXDEV, "Invalid cross-device link")


def test_hardlink_builtin_disabled_by_default():
    candidate = load_candidate()
    assert candidate.source == "builtin"
    assert candidate.manifest.default_enabled is False


async def test_on_organized_maps_longest_prefix_of_same_downloader_and_links(
    roots, tmp_path
):
    downloads, library = roots
    wrong = str(tmp_path / "wrong")
    plugin, ctx = make_plugin(
        roots,
        path_map=[
            {"from": "/dl", "to": wrong},
            {"from": "/dl/Bangumi", "to": str(downloads / "Bangumi")},
            {"downloader": "other", "from": "/dl/Bangumi/Anime (2024)", "to": wrong},
        ],
    )
    src = write(downloads / SEASON / "Anime S01E01.mkv", "v1")
    sub = write(downloads / SEASON / "Anime S01E01.zh.ass", "sub")

    await plugin.on_organized(organized(src.name, sub.name))

    assert os.path.samefile(src, library / SEASON / src.name)
    assert os.path.samefile(sub, library / SEASON / sub.name)
    assert ctx.bus.published == []


@pytest.mark.parametrize("mode", ["copy", "symlink", "skip"])
async def test_on_organized_cross_device_applies_policy(roots, monkeypatch, mode):
    downloads, library = roots
    plugin, ctx = make_plugin(roots, cross_device=mode)
    src = write(downloads / SEASON / "Anime S01E01.mkv", "v1")
    monkeypatch.setattr(os, "link", exdev)

    await plugin.on_organized(organized(src.name))

    dst = library / SEASON / src.name
    if mode == "skip":
        assert not dst.exists()
        [event] = ctx.bus.published
        assert event.kind == "hardlink.failed" and src.name in event.files
        return
    assert dst.read_text() == "v1"
    assert dst.is_symlink() is (mode == "symlink")
    assert ctx.bus.published == []


async def test_on_organized_redelivery_does_not_copy_again(roots, monkeypatch):
    downloads, library = roots
    plugin, ctx = make_plugin(roots)
    src = write(downloads / SEASON / "Anime S01E01.mkv", "v1")
    monkeypatch.setattr(os, "link", exdev)
    copies: list[object] = []

    def copy2(a, b):
        copies.append(b)
        return shutil.copyfile(a, b)

    monkeypatch.setattr(shutil, "copy2", copy2)

    await plugin.on_organized(organized(src.name))
    await plugin.on_organized(organized(src.name))

    assert len(copies) == 1
    assert ctx.bus.published == []


async def test_on_organized_interrupted_copy_leaves_no_target(roots, monkeypatch):
    downloads, library = roots
    plugin, ctx = make_plugin(roots)
    src = write(downloads / SEASON / "Anime S01E01.mkv", "v1")
    monkeypatch.setattr(os, "link", exdev)
    real_copy2 = shutil.copy2

    def disk_full(a, b):
        Path(b).write_text("v")
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(shutil, "copy2", disk_full)
    await plugin.on_organized(organized(src.name))
    monkeypatch.setattr(shutil, "copy2", real_copy2)
    # 半个文件不能留在目标位置，否则重试时会被当成「不是本插件创建的」冲突
    await plugin.on_organized(organized(src.name))

    assert (library / SEASON / src.name).read_text() == "v1"
    assert [p.name for p in (library / SEASON).iterdir()] == [src.name]
    [failed] = ctx.bus.published
    assert "No space left" in failed.files


async def test_on_organized_revision_upgrade_replaces_own_link(roots):
    downloads, library = roots
    plugin, ctx = make_plugin(roots)
    src = write(downloads / SEASON / "Anime S01E01.mkv", "v1")
    await plugin.on_organized(organized(src.name))
    # V2 经 revision saga 替换后落在同一规范路径，但已是另一个文件
    src.unlink()
    write(src, "v2")

    await plugin.on_organized(organized(src.name))

    dst = library / SEASON / src.name
    assert os.path.samefile(src, dst) and dst.read_text() == "v2"
    assert [p.name for p in dst.parent.iterdir()] == [src.name]
    assert ctx.bus.published == []


async def test_on_organized_problem_files_kept_and_notified_once(roots, tmp_path):
    downloads, library = roots
    plugin, ctx = make_plugin(
        roots,
        path_map=[
            {"from": "/dl", "to": str(downloads)},
            {"from": f"/dl/{SEASON}/outside", "to": str(tmp_path / "elsewhere")},
        ],
    )
    taken = write(downloads / SEASON / "Anime S01E01.mkv", "new")
    write(library / SEASON / taken.name, "user file")
    write(tmp_path / "elsewhere" / "x.mkv", "x")

    await plugin.on_organized(organized(taken.name, "outside/x.mkv"))

    assert (library / SEASON / taken.name).read_text() == "user file"
    [event] = ctx.bus.published
    assert event.kind == "hardlink.failed" and event.torrent_hash == "h1"
    assert taken.name in event.files and "x.mkv" in event.files


def test_backfill_route_links_existing_files_and_counts(roots):
    downloads, library = roots
    plugin, ctx = make_plugin(roots)
    for name in ("new.mkv", "new.zh.ass", "foreign.mkv", "note.nfo", "part.mkv.!qB"):
        write(downloads / SEASON / name, name)
    write(library / SEASON / "foreign.mkv", "user file")
    linked = write(downloads / SEASON / "linked.mkv", "linked")
    (library / SEASON).mkdir(parents=True, exist_ok=True)
    os.link(linked, library / SEASON / "linked.mkv")
    app = FastAPI()
    app.include_router(plugin.api())

    resp = TestClient(app).post("/backfill")

    assert resp.json() == {"linked": 2, "exists": 1, "conflict": 1, "failed": 0}
    assert os.path.samefile(
        downloads / SEASON / "new.zh.ass", library / SEASON / "new.zh.ass"
    )
    assert not (library / SEASON / "note.nfo").exists()
    assert ctx.bus.published == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"source_root": "downloads"},
        {"library_root": "library"},
        {"library_root": "/downloads/library", "source_root": "/downloads"},
    ],
)
def test_options_invalid_roots_rejected(overrides):
    model = load_candidate().load().config_model
    with pytest.raises(ValidationError):
        model.model_validate(
            {"source_root": "/downloads", "library_root": "/media", **overrides}
        )


async def test_on_organized_unrecorded_own_copy_adopted_and_upgraded(
    roots, monkeypatch
):
    downloads, library = roots
    plugin, ctx = make_plugin(roots)
    src = write(downloads / SEASON / "Anime S01E01.mkv", "v1")
    monkeypatch.setattr(os, "link", exdev)
    # 上次复制已放到目标位置，但协程被取消或进程退出，所有权没来得及记录
    dst = library / SEASON / src.name
    dst.parent.mkdir(parents=True)
    shutil.copy2(src, dst)

    await plugin.on_organized(organized(src.name))
    src.unlink()
    write(src, "v2")
    await plugin.on_organized(organized(src.name))

    assert dst.read_text() == "v2"
    assert ctx.bus.published == []


async def test_on_organized_user_file_at_former_link_kept(roots):
    downloads, library = roots
    plugin, ctx = make_plugin(roots)
    src = write(downloads / SEASON / "Anime S01E01.mkv", "v1")
    await plugin.on_organized(organized(src.name))
    # 用户删掉插件的链接，在同一位置放了自己的文件
    dst = library / SEASON / src.name
    dst.unlink()
    write(dst, "user file")
    src.unlink()
    write(src, "v2")

    await plugin.on_organized(organized(src.name))

    assert dst.read_text() == "user file"
    [event] = ctx.bus.published
    assert event.kind == "hardlink.failed" and src.name in event.files


async def test_link_concurrent_copies_of_same_target_all_succeed(roots, monkeypatch):
    downloads, library = roots
    plugin, ctx = make_plugin(roots)
    src = write(downloads / SEASON / "Anime S01E01.mkv", "v1")
    monkeypatch.setattr(os, "link", exdev)
    both_copying = threading.Barrier(2, timeout=5)

    def copy2(a, b):
        both_copying.wait()
        return shutil.copyfile(a, b)

    monkeypatch.setattr(shutil, "copy2", copy2)

    # 补链与订阅同时处理同一个目标
    results = await asyncio.gather(plugin.link(src), plugin.link(src))

    assert [status for status, _ in results] == ["linked", "linked"]
    dst = library / SEASON / src.name
    assert dst.read_text() == "v1"
    assert [p.name for p in dst.parent.iterdir()] == [src.name]
