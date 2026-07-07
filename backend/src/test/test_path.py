"""Tests for path helpers: save path generation, file classification, parsing."""

from unittest.mock import patch

from module.downloader.path import (
    check_files,
    file_depth,
    gen_save_path,
    is_ep,
    path_to_bangumi,
    rule_name,
    sanitize_path_fragment,
)
from test.factories import make_bangumi

# ---------------------------------------------------------------------------
# sanitize_path_fragment
# ---------------------------------------------------------------------------


class TestSanitizePathFragment:
    def test_replaces_reserved_characters(self):
        assert sanitize_path_fragment('A<B>C:D"E/F\\G|H?I*J') == "A B C D E F G H I J"

    def test_collapses_whitespace_and_strips_trailing_dots(self):
        assert sanitize_path_fragment("Name  ...") == "Name"

    def test_preserves_cjk_and_brackets(self):
        assert (
            sanitize_path_fragment("[Sub] 孤独摇滚！(2022)") == "[Sub] 孤独摇滚！(2022)"
        )

    def test_idempotent(self):
        once = sanitize_path_fragment("Fate/Zero: Part?2")
        assert sanitize_path_fragment(once) == once

    def test_all_reserved_title_falls_back_in_save_path(self):
        """全保留字符的标题不能让保存路径坍缩出空目录层。"""
        bangumi = make_bangumi(official_title="??", year=None)
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            result = gen_save_path(bangumi)

        assert "//" not in result
        assert "Unknown Bangumi" in result


# ---------------------------------------------------------------------------
# gen_save_path
# ---------------------------------------------------------------------------


class TestGenSavePath:
    def test_with_year(self):
        """Save path includes (year) when year is set."""
        bangumi = make_bangumi(official_title="My Anime", year="2024", season=2)
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            result = gen_save_path(bangumi)

        assert "My Anime (2024)" in result
        assert "Season 2" in result

    def test_reserved_characters_sanitized_in_folder(self):
        """标题里的保留字符不能把保存路径拆成多级目录 (#721)。"""
        bangumi = make_bangumi(official_title="Fate/Zero: Part?2", year="2024")
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            result = gen_save_path(bangumi)

        assert "Fate Zero Part 2 (2024)" in result
        assert result.count("/") == 4  # /downloads/Bangumi/<folder>/Season 1

    def test_without_year(self):
        """Save path omits year parentheses when year is None."""
        bangumi = make_bangumi(official_title="My Anime", year=None, season=1)
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            result = gen_save_path(bangumi)

        assert "My Anime" in result
        assert "()" not in result
        assert "Season 1" in result

    def test_season_formatting(self):
        """Season is a plain integer, not zero-padded in path."""
        bangumi = make_bangumi(season=10)
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            result = gen_save_path(bangumi)

        assert "Season 10" in result

    def test_with_different_base_path(self):
        """Works with different base download path."""
        bangumi = make_bangumi(official_title="Test", year="2025", season=3)
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/mnt/media/Bangumi"
            result = gen_save_path(bangumi)

        assert result.startswith("/mnt/media/Bangumi")
        assert "Test (2025)" in result
        assert "Season 3" in result

    def test_movie_layout_omits_season_folder(self):
        """Movies use a flat 'Title (Year)' layout with no Season subfolder."""
        bangumi = make_bangumi(
            official_title="天气之子", year="2019", season=1, episode_type="movie"
        )
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            result = gen_save_path(bangumi)

        assert result == "/downloads/Bangumi/天气之子 (2019)"
        assert "Season" not in result

    def test_special_uses_season_zero(self):
        """Specials/OVA/OAD (season=0) land in Season 0, Jellyfin/Plex convention."""
        bangumi = make_bangumi(
            official_title="My Anime", year="2024", season=0, episode_type="special"
        )
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            result = gen_save_path(bangumi)

        assert result == "/downloads/Bangumi/My Anime (2024)/Season 0"

    def test_gen_save_path_regular_offset_to_zero_reverts_to_original_season(self):
        """普通剧集 season+offset 落到 0 时回退原季号：Season 0 会被
        Plex/Jellyfin 当作特别篇，只有 special 类型才允许落入。"""
        bangumi = make_bangumi(
            official_title="My Anime",
            year="2024",
            season=1,
            season_offset=-1,
            episode_type="episode",
        )
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            result = gen_save_path(bangumi)

        assert result == "/downloads/Bangumi/My Anime (2024)/Season 1"

    def test_gen_save_path_special_offset_to_zero_lands_in_season_zero(self):
        """特别篇（special）经偏移落到第 0 季是合法的（Jellyfin/Plex 惯例）。"""
        bangumi = make_bangumi(
            official_title="My Anime",
            year="2024",
            season=1,
            season_offset=-1,
            episode_type="special",
        )
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            result = gen_save_path(bangumi)

        assert result == "/downloads/Bangumi/My Anime (2024)/Season 0"

    def test_gen_save_path_special_offset_below_zero_reverts_to_original_season(self):
        """特别篇偏移到负季号仍属非法配置，回退原季号。"""
        bangumi = make_bangumi(
            official_title="My Anime",
            year="2024",
            season=0,
            season_offset=-1,
            episode_type="special",
        )
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            result = gen_save_path(bangumi)

        assert result == "/downloads/Bangumi/My Anime (2024)/Season 0"


# ---------------------------------------------------------------------------
# rule_name
# ---------------------------------------------------------------------------


class TestRuleName:
    def test_without_group_tag(self):
        """Rule name without group tag is just title and season."""
        bangumi = make_bangumi(official_title="My Anime", season=1, group_name="Sub")
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.bangumi_manage.group_tag = False
            result = rule_name(bangumi)

        assert result == "My Anime S1"

    def test_with_group_tag(self):
        """Rule name with group tag includes [group] prefix."""
        bangumi = make_bangumi(
            official_title="My Anime", season=2, group_name="SubGroup"
        )
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.bangumi_manage.group_tag = True
            result = rule_name(bangumi)

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
        media, subs = check_files(files)

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
        media, subs = check_files(files)

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
        media, subs = check_files(files)

        assert len(media) == 2
        assert len(subs) == 2

    def test_empty_file_list(self):
        """Empty file list returns empty lists."""
        media, subs = check_files([])
        assert media == []
        assert subs == []

    def test_nested_paths(self):
        """Files in subdirectories are handled correctly."""
        files = [
            {"name": "Season 1/episode01.mkv"},
            {"name": "Subs/episode01.ass"},
        ]
        media, subs = check_files(files)

        assert len(media) == 1
        assert len(subs) == 1


# ---------------------------------------------------------------------------
# path_to_bangumi
# ---------------------------------------------------------------------------


class TestPathToBangumi:
    def test_extracts_name_and_season(self):
        """Parses save_path to extract bangumi name and season number."""
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            name, season = path_to_bangumi(
                "/downloads/Bangumi/My Anime (2024)/Season 2"
            )

        assert name == "My Anime (2024)"
        assert season == 2

    def test_season_1_default(self):
        """When no Season pattern found, defaults to season 1."""
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            name, season = path_to_bangumi("/downloads/Bangumi/My Anime (2024)")

        assert name == "My Anime (2024)"
        assert season == 1

    def test_s_prefix_pattern(self):
        """Recognizes S01 style season naming."""
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            name, season = path_to_bangumi("/downloads/Bangumi/Anime/S03")

        assert season == 3


# ---------------------------------------------------------------------------
# is_ep / file_depth
# ---------------------------------------------------------------------------


class TestIsEp:
    def test_shallow_file(self):
        """File at depth 1 (just filename) is considered an episode."""
        assert is_ep("episode.mkv") is True

    def test_one_folder_deep(self):
        """File at depth 2 (one folder) is still an episode."""
        assert is_ep("Season 1/episode.mkv") is True

    def test_too_deep(self):
        """File at depth 3+ is NOT considered an episode."""
        assert is_ep("a/b/episode.mkv") is False

    def test_file_depth(self):
        """file_depth returns correct part count."""
        assert file_depth("file.mkv") == 1
        assert file_depth("a/file.mkv") == 2
        assert file_depth("a/b/c/file.mkv") == 4
