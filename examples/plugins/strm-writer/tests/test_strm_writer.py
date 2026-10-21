import asyncio
import logging

import pytest
from strm_writer import StrmWriter

from ab_sdk.events import OrganizedFile, TorrentOrganized
from ab_sdk.testing import create_plugin

MEDIA = "/downloads/Bangumi/A/Season 1/A S01E01.mkv"


def organized(*files: OrganizedFile) -> TorrentOrganized:
    return TorrentOrganized(torrent_hash="h", bangumi_id=1, files=files)


def run(tmp_path, url_prefix: str, *files: OrganizedFile) -> None:
    options = {
        "strm_root": str(tmp_path / "STRM"),
        "url_prefix": url_prefix,
        "media_root": "/downloads/Bangumi/",
    }
    plugin, _ = create_plugin(StrmWriter, options)
    asyncio.run(plugin.on_organized(organized(*files)))


@pytest.mark.parametrize(
    ("url_prefix", "content"),
    [
        (
            "http://nas:8096/media/",
            "http://nas:8096/media/A/Season%201/A%20S01E01.mkv",
        ),
        ("/mnt/cloud/", "/mnt/cloud/A/Season 1/A S01E01.mkv"),
    ],
)
def test_on_organized_mirrors_media_path_into_strm(tmp_path, url_prefix, content):
    run(
        tmp_path,
        url_prefix,
        OrganizedFile(MEDIA, "media"),
        OrganizedFile(MEDIA.replace(".mkv", ".ass"), "subtitle"),
    )
    season = tmp_path / "STRM" / "A" / "Season 1"
    assert [p.name for p in season.iterdir()] == ["A S01E01.strm"]
    assert (season / "A S01E01.strm").read_text(encoding="utf-8") == content


def test_on_organized_prefix_change_rewrites_strm(tmp_path):
    run(tmp_path, "http://old/", OrganizedFile(MEDIA, "media"))
    run(tmp_path, "http://new/", OrganizedFile(MEDIA, "media"))
    strm = tmp_path / "STRM" / "A" / "Season 1" / "A S01E01.strm"
    assert strm.read_text(encoding="utf-8").startswith("http://new/")


@pytest.mark.parametrize(
    "path", ["/other/A S01E01.mkv", "/downloads/Bangumi/../../etc/x.mkv"]
)
def test_on_organized_path_outside_media_root_is_skipped(tmp_path, caplog, path):
    with caplog.at_level(logging.WARNING):
        run(tmp_path, "http://nas/", OrganizedFile(path, "media"))
    assert not (tmp_path / "STRM").exists()
    assert "不在媒体根目录" in caplog.text
