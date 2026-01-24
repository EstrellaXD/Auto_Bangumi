"""Tests for TorrentPath: save path generation, file classification, parsing."""

import pytest
from unittest.mock import patch

from module.downloader.path import TorrentPath
from module.models import Bangumi, BangumiUpdate

from test.factories import make_bangumi


@pytest.fixture
def torrent_path():
    return TorrentPath()


# ---------------------------------------------------------------------------
# _gen_save_path
# ---------------------------------------------------------------------------


class TestGenSavePath:
    def test_with_year(self):
        """Save path includes (year) when year is set."""
        bangumi = make_bangumi(official_title="My Anime", year="2024", season=2)
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            result = TorrentPath._gen_save_path(bangumi)

        assert "My Anime (2024)" in result
        assert "Season 2" in result

    def test_without_year(self):
        """Save path omits year parentheses when year is None."""
        bangumi = make_bangumi(official_title="My Anime", year=None, season=1)
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            result = TorrentPath._gen_save_path(bangumi)

        assert "My Anime" in result
        assert "()" not in result
        assert "Season 1" in result

    def test_season_formatting(self):
        """Season is a plain integer, not zero-padded in path."""
        bangumi = make_bangumi(season=10)
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            result = TorrentPath._gen_save_path(bangumi)

        assert "Season 10" in result

    def test_with_different_base_path(self):
        """Works with different base download path."""
        bangumi = make_bangumi(official_title="Test", year="2025", season=3)
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/mnt/media/Bangumi"
            result = TorrentPath._gen_save_path(bangumi)

        assert result.startswith("/mnt/media/Bangumi")
        assert "Test (2025)" in result
        assert "Season 3" in result


# ---------------------------------------------------------------------------
# _rule_name
# ---------------------------------------------------------------------------


class TestRuleName:
    def test_without_group_tag(self):
        """Rule name without group tag is just title and season."""
        bangumi = make_bangumi(official_title="My Anime", season=1, group_name="Sub")
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.bangumi_manage.group_tag = False
            result = TorrentPath._rule_name(bangumi)

        assert result == "My Anime S1"

    def test_with_group_tag(self):
        """Rule name with group tag includes [group] prefix."""
        bangumi = make_bangumi(official_title="My Anime", season=2, group_name="SubGroup")
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.bangumi_manage.group_tag = True
            result = TorrentPath._rule_name(bangumi)

        assert result == "[SubGroup] My Anime S2"


# ---------------------------------------------------------------------------
# check_files
# ---------------------------------------------------------------------------


class TestCheckFiles:
    def test_separates_media_and_subtitles(self):
        """Media files (.mp4/.mkv) and subtitle files (.ass/.srt) are separated."""
        files = [
            {"name": "episode01.mkv"},
            {"name": "episode01.ass"},
            {"name": "episode02.mp4"},
            {"name": "episode02.srt"},
        ]
        media, subs = TorrentPath.check_files(files)

        assert len(media) == 2
        assert "episode01.mkv" in media
        assert "episode02.mp4" in media
        assert len(subs) == 2
        assert "episode01.ass" in subs
        assert "episode02.srt" in subs

    def test_ignores_other_extensions(self):
        """Files with non-media, non-subtitle extensions are ignored."""
        files = [
            {"name": "episode.mkv"},
            {"name": "readme.txt"},
            {"name": "info.nfo"},
            {"name": "cover.jpg"},
        ]
        media, subs = TorrentPath.check_files(files)

        assert len(media) == 1
        assert len(subs) == 0

    def test_case_insensitive_extensions(self):
        """Extension matching is case-insensitive."""
        files = [
            {"name": "episode.MKV"},
            {"name": "episode.MP4"},
            {"name": "sub.ASS"},
            {"name": "sub.SRT"},
        ]
        media, subs = TorrentPath.check_files(files)

        assert len(media) == 2
        assert len(subs) == 2

    def test_empty_file_list(self):
        """Empty file list returns empty lists."""
        media, subs = TorrentPath.check_files([])
        assert media == []
        assert subs == []

    def test_nested_paths(self):
        """Files in subdirectories are handled correctly."""
        files = [
            {"name": "Season 1/episode01.mkv"},
            {"name": "Subs/episode01.ass"},
        ]
        media, subs = TorrentPath.check_files(files)

        assert len(media) == 1
        assert len(subs) == 1


# ---------------------------------------------------------------------------
# _path_to_bangumi
# ---------------------------------------------------------------------------


class TestPathToBangumi:
    def test_extracts_name_and_season(self):
        """Parses save_path to extract bangumi name and season number."""
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            tp = TorrentPath()
            name, season = tp._path_to_bangumi(
                "/downloads/Bangumi/My Anime (2024)/Season 2"
            )

        assert name == "My Anime (2024)"
        assert season == 2

    def test_season_1_default(self):
        """When no Season pattern found, defaults to season 1."""
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            tp = TorrentPath()
            name, season = tp._path_to_bangumi("/downloads/Bangumi/My Anime (2024)")

        assert name == "My Anime (2024)"
        assert season == 1

    def test_s_prefix_pattern(self):
        """Recognizes S01 style season naming."""
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            tp = TorrentPath()
            name, season = tp._path_to_bangumi("/downloads/Bangumi/Anime/S03")

        assert season == 3


# ---------------------------------------------------------------------------
# is_ep / _file_depth
# ---------------------------------------------------------------------------


class TestIsEp:
    def test_shallow_file(self):
        """File at depth 1 (just filename) is considered an episode."""
        tp = TorrentPath()
        assert tp.is_ep("episode.mkv") is True

    def test_one_folder_deep(self):
        """File at depth 2 (one folder) is still an episode."""
        tp = TorrentPath()
        assert tp.is_ep("Season 1/episode.mkv") is True

    def test_too_deep(self):
        """File at depth 3+ is NOT considered an episode."""
        tp = TorrentPath()
        assert tp.is_ep("a/b/episode.mkv") is False

    def test_file_depth(self):
        """_file_depth returns correct part count."""
        tp = TorrentPath()
        assert tp._file_depth("file.mkv") == 1
        assert tp._file_depth("a/file.mkv") == 2
        assert tp._file_depth("a/b/c/file.mkv") == 4
