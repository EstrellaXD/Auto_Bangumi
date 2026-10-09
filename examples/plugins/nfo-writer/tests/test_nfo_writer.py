import asyncio

from nfo_writer import NfoWriter

from ab_sdk.events import OrganizedFile, TorrentOrganized
from ab_sdk.testing import create_plugin


def organized(*files: OrganizedFile) -> TorrentOrganized:
    return TorrentOrganized(torrent_hash="h", bangumi_id=1, files=files)


def run(plugin, event) -> None:
    asyncio.run(plugin.on_organized(event))


def test_on_organized_writes_nfo_next_to_media_with_path_map(tmp_path):
    season = tmp_path / "Show & Co" / "Season 1"
    season.mkdir(parents=True)
    plugin, _ = create_plugin(
        NfoWriter, {"path_from": "/downloads", "path_to": str(tmp_path)}
    )
    event = organized(
        OrganizedFile("/downloads/Show & Co/Season 1/Show S01E05.mkv", "media"),
        OrganizedFile("/downloads/Show & Co/Season 1/Show S01E05.zh.ass", "subtitle"),
    )
    run(plugin, event)
    nfo = (season / "Show S01E05.nfo").read_text(encoding="utf-8")
    assert "<showtitle>Show &amp; Co</showtitle>" in nfo
    assert "<season>1</season>" in nfo and "<episode>5</episode>" in nfo
    assert [p.name for p in season.iterdir()] == ["Show S01E05.nfo"]


def test_on_organized_existing_nfo_is_not_overwritten(tmp_path):
    media = tmp_path / "Show" / "Season 1" / "Show S01E01.mkv"
    media.parent.mkdir(parents=True)
    nfo = media.with_suffix(".nfo")
    nfo.write_text("mine", encoding="utf-8")
    plugin, _ = create_plugin(NfoWriter)
    run(plugin, organized(OrganizedFile(str(media), "media")))
    assert nfo.read_text(encoding="utf-8") == "mine"


def test_on_organized_name_without_episode_marker_writes_nothing(tmp_path):
    media = tmp_path / "Movie (2024).mkv"
    plugin, _ = create_plugin(NfoWriter)
    run(plugin, organized(OrganizedFile(str(media), "media")))
    assert list(tmp_path.iterdir()) == []
