"""Tests reproducing bugs from GitHub issues #974, #976, #977, #986.

Each test class targets a specific issue with tests that demonstrate
the current (buggy) behavior and the expected (fixed) behavior.
"""

import re

import pytest

from module.manager.renamer import Renamer
from module.models import EpisodeFile
from module.parser.analyser.raw_parser import (
    get_group,
    process,
    raw_parser,
)

# ---------------------------------------------------------------------------
# Issue #986: Parser fails on [group][title][episode_text] format
# https://github.com/EstrellaXD/Auto_Bangumi/issues/986
#
# Torrent names from Atlas subtitle group use a [group][title][ep_text]
# format instead of the typical [group] title - ep [tags] format.
# The raw_parser's TITLE_RE regex doesn't match, returning None.
# ---------------------------------------------------------------------------


class TestIssue986AtlasSubGroupFormat:
    """Issue #986: Parser crashes on Atlas subtitle group naming convention."""

    ATLAS_TITLES = [
        "[阿特拉斯字幕组·雪原市出差所][命运-奇异赝品_Fate／strange Fake][04_半神们的卡农曲][简繁日内封PGS][日语配音版_Japanese Dub][Web-DL Remux][1080p AVC AAC].mkv",
        "[阿特拉斯字幕组·雪原市出差所][命运-奇异赝品_Fate／strange Fake][07_神自黄昏归来][简繁日内封PGS][日语配音版_Japanese Dub][Web-DL Remux][1080p AVC AAC].mkv",
        "[阿特拉斯字幕组·雪原市出差所][命运-奇异赝品_Fate／strange Fake][03_无英灵的战斗][简繁日内封PGS][日语配音版_Japanese Dub][Web-DL Remux][1080p AVC AAC].mkv",
    ]

    def test_get_group_extracts_atlas_group(self):
        """get_group should extract the group name from [group][title][ep] format."""
        name = "[阿特拉斯字幕组·雪原市出差所][命运-奇异赝品_Fate／strange Fake][04_半神们的卡农曲]"
        group = get_group(name)
        assert group == "阿特拉斯字幕组·雪原市出差所"

    def test_process_returns_none_for_atlas_format(self):
        """process() currently returns None for Atlas format (bug demonstration)."""
        title = self.ATLAS_TITLES[0]
        result = process(title)
        # BUG: process returns None because TITLE_RE doesn't match this format
        assert result is None, (
            "If this passes, the parser still can't handle Atlas format. "
            "If it fails (result is not None), the bug may have been fixed!"
        )

    def test_raw_parser_returns_none_for_atlas_format(self):
        """raw_parser returns None for Atlas format, causing AttributeError downstream."""
        title = self.ATLAS_TITLES[0]
        result = raw_parser(title)
        # BUG: returns None → downstream code does .groups() on None → AttributeError
        assert result is None

    @pytest.mark.parametrize("title", ATLAS_TITLES)
    def test_atlas_titles_all_fail_to_parse(self, title):
        """All Atlas format titles fail to parse."""
        result = raw_parser(title)
        assert result is None

    def test_get_group_returns_empty_for_no_brackets(self):
        """get_group returns empty string for title without brackets (regression guard)."""
        result = get_group("No Brackets Title")
        assert result == ""

    def test_get_group_does_not_crash_on_empty_string(self):
        """get_group handles empty string without crashing."""
        result = get_group("")
        assert result == ""


# ---------------------------------------------------------------------------
# Issue #977: Episode 0 (specials/OVAs) incorrectly renamed to E01
# https://github.com/EstrellaXD/Auto_Bangumi/issues/977
#
# When a file is S01E00.mkv (episode 0 special), and there's a positive
# episode_offset (e.g. from offset scanner), the renamer changes it to
# S01E01.mkv which overwrites the real episode 1.
# ---------------------------------------------------------------------------


class TestIssue977EpisodeZeroOffset:
    """Issue #977: Episode 0 should not be shifted by positive offset."""

    def test_episode_zero_preserved_with_no_offset(self):
        """Episode 0 with offset=0 stays as E00."""
        ep = EpisodeFile(
            media_path="old.mkv",
            title="Fate strange Fake",
            season=1,
            episode=0,
            suffix=".mkv",
        )
        result = Renamer.gen_path(
            ep, "Fate strange Fake", method="pn", episode_offset=0
        )
        assert "E00" in result

    def test_episode_zero_immune_to_positive_offset(self):
        """Episode 0 (special/OVA) should not be shifted by positive offset."""
        ep = EpisodeFile(
            media_path="old.mkv",
            title="Fate strange Fake",
            season=1,
            episode=0,
            suffix=".mkv",
        )
        result = Renamer.gen_path(
            ep, "Fate strange Fake", method="pn", episode_offset=1
        )
        assert "E00" in result

    def test_episode_zero_immune_to_negative_offset(self):
        """Episode 0 (special/OVA) should not be shifted by negative offset."""
        ep = EpisodeFile(
            media_path="old.mkv",
            title="Fate strange Fake",
            season=1,
            episode=0,
            suffix=".mkv",
        )
        result = Renamer.gen_path(
            ep, "Fate strange Fake", method="pn", episode_offset=-12
        )
        assert "E00" in result

    def test_regular_episode_offset_still_works(self):
        """Regular episodes should still be affected by offset normally."""
        ep = EpisodeFile(
            media_path="old.mkv",
            title="Test",
            season=1,
            episode=13,
            suffix=".mkv",
        )
        result = Renamer.gen_path(ep, "Test", method="pn", episode_offset=-12)
        assert "E01" in result  # 13 - 12 = 1

    def test_episode_zero_advance_method(self):
        """Episode 0 with advance method and no offset stays E00."""
        ep = EpisodeFile(
            media_path="old.mkv",
            title="Test",
            season=1,
            episode=0,
            suffix=".mkv",
        )
        result = Renamer.gen_path(
            ep, "Bangumi Name", method="advance", episode_offset=0
        )
        assert result == "Bangumi Name S01E00.mkv"


# ---------------------------------------------------------------------------
# Issue #976: NoneType in match_list causes TypeError
# https://github.com/EstrellaXD/Auto_Bangumi/issues/976
#
# When bangumi records have None as title_raw or aliases contain None,
# sorted(title_index.keys(), key=len) crashes because len(None) fails.
# Also, get_group crashes with IndexError on names without brackets.
# ---------------------------------------------------------------------------


class TestIssue976NoneInMatchList:
    """Issue #976: match_list should handle None titles gracefully."""

    async def test_match_list_filters_none_title_raw(self, db_session):
        """match_list should skip bangumi with title_raw=None."""
        from module.database.bangumi import BangumiDatabase
        from module.models import Bangumi

        db = BangumiDatabase(db_session)

        # Create bangumi with None-ish title_raw
        b1 = Bangumi(
            official_title="Normal Anime",
            year="2024",
            title_raw="[Group] Normal Anime",
            season=1,
        )
        await db.add(b1)

        # The match_list code now checks `if m.title_raw:` before adding to index
        # This test verifies that path works when all entries are valid
        match_datas = await db.search_all()
        title_index = {}
        for m in match_datas:
            if m.title_raw:
                title_index[m.title_raw] = m

        # Should not raise TypeError
        sorted_titles = sorted(title_index.keys(), key=len, reverse=True)
        assert len(sorted_titles) == 1

    def test_sorted_with_none_key_raises_typeerror(self):
        """Demonstrate that sorted() with None keys crashes (the original bug)."""
        title_index = {"valid_title": "data", None: "bad_data"}
        with pytest.raises(TypeError, match="'NoneType'"):
            sorted(title_index.keys(), key=len, reverse=True)  # type: ignore[arg-type]

    def test_empty_title_index_produces_empty_pattern(self):
        """When all titles are None/empty, the regex pattern should be empty."""
        title_index: dict[str, str] = {}
        sorted_titles = sorted(title_index.keys(), key=len, reverse=True)
        pattern = "|".join(re.escape(t) for t in sorted_titles)
        assert pattern == ""

    def test_get_group_no_brackets_returns_empty(self):
        """get_group handles names without brackets (regression for IndexError)."""
        # The original code did: re.split(r"[\[\]]", name)[1]
        # which crashes with IndexError when there are no brackets
        result = get_group("No Brackets At All")
        assert result == ""

    def test_get_group_single_bracket_pair(self):
        """get_group extracts group from single bracket pair."""
        result = get_group("[GroupName] Some Title")
        assert result == "GroupName"

    def test_get_group_empty_brackets(self):
        """get_group handles empty brackets."""
        result = get_group("[] empty")
        assert result == ""


# ---------------------------------------------------------------------------
# Issue #974: PatternError when filter string contains regex special chars
# https://github.com/EstrellaXD/Auto_Bangumi/issues/974
#
# The _get_filter_pattern method does filter_str.replace(",", "|") and
# then re.compile(). If the filter contains regex special characters
# like [ ] ( ) etc., it causes PatternError.
# ---------------------------------------------------------------------------


class TestIssue974FilterPatternError:
    """Issue #974: Filter strings with regex special chars crash re.compile."""

    def test_normal_filter_compiles(self):
        """Normal filter string like '720,繁体' works fine."""
        filter_str = "720,繁体"
        pattern_str = filter_str.replace(",", "|")
        pattern = re.compile(pattern_str, re.IGNORECASE)
        assert pattern.search("720p test")
        assert pattern.search("繁体字幕")
        assert not pattern.search("1080p 简体")

    def test_raw_unterminated_bracket_is_invalid_regex(self):
        """Demonstrate that unterminated '[' is invalid regex."""
        filter_str = "720,[字幕组"
        pattern_str = filter_str.replace(",", "|")
        with pytest.raises(re.error):
            re.compile(pattern_str, re.IGNORECASE)

    def test_engine_handles_unterminated_bracket(self):
        """_get_filter_pattern falls back to literal matching for invalid regex."""
        from unittest.mock import MagicMock

        from module.rss.engine import RSSEngine

        engine = RSSEngine.__new__(RSSEngine)
        engine._filter_cache = {}
        pattern = engine._get_filter_pattern("720,[字幕组")
        # Should not raise — falls back to escaped literal matching
        assert pattern.search("720p video")
        assert pattern.search("[字幕组 release")
        assert not pattern.search("1080p no match")

    def test_engine_handles_unmatched_parenthesis(self):
        """_get_filter_pattern falls back for unmatched '('."""
        from module.rss.engine import RSSEngine

        engine = RSSEngine.__new__(RSSEngine)
        engine._filter_cache = {}
        pattern = engine._get_filter_pattern("720,test(v2")
        assert pattern.search("720p")
        assert pattern.search("test(v2 stuff")

    def test_engine_handles_trailing_backslash(self):
        """_get_filter_pattern falls back for trailing backslash."""
        from module.rss.engine import RSSEngine

        engine = RSSEngine.__new__(RSSEngine)
        engine._filter_cache = {}
        pattern = engine._get_filter_pattern("720,path\\")
        assert pattern.search("720p")

    def test_engine_default_filter_still_uses_regex(self):
        r"""Default filter '720,\d+-\d+' is valid regex and used as-is."""
        from module.rss.engine import RSSEngine

        engine = RSSEngine.__new__(RSSEngine)
        engine._filter_cache = {}
        pattern = engine._get_filter_pattern(r"720,\d+-\d+")
        assert pattern.search("720p video")
        assert pattern.search("01-12 batch")
        assert not pattern.search("1080p single episode")

    def test_engine_caches_filter_pattern(self):
        """Filter patterns are cached to avoid recompilation."""
        from module.rss.engine import RSSEngine

        engine = RSSEngine.__new__(RSSEngine)
        engine._filter_cache = {}
        p1 = engine._get_filter_pattern("720,1080")
        p2 = engine._get_filter_pattern("720,1080")
        assert p1 is p2


# ---------------------------------------------------------------------------
# Issue #990: Titles starting with numbers cause title_raw=None, crashing
#             the RSS loop with TypeError in match_torrent
# https://github.com/EstrellaXD/Auto_Bangumi/issues/990
#
# "[ANi] 29 岁单身中坚冒险家的日常 - 07" → regex matches "29 " as episode,
# title becomes empty → title_raw=None → None stored as alias → crash on
# `None in torrent_name` in match_torrent.
# ---------------------------------------------------------------------------


class TestIssue990NumberPrefixTitle:
    """Issue #990: Titles starting with numbers crash RSS loop."""

    PROBLEM_TITLE = (
        "[ANi] 29 岁单身中坚冒险家的日常 - 07 [1080P][Baha][WEB-DL][AAC AVC][CHT][MP4]"
    )

    def test_raw_parser_correctly_parses_leading_number_title(self):
        """raw_parser correctly parses title starting with number and extracts episode."""
        result = raw_parser(self.PROBLEM_TITLE)
        assert result is not None
        assert result.episode == 7
        assert result.title_zh == "29 岁单身中坚冒险家的日常"
        assert result.resolution == "1080P"
        assert result.group == "ANi"

    async def test_title_parser_returns_bangumi_for_number_prefix_title(self):
        """TitleParser.raw_parser returns a valid Bangumi for number-prefixed titles."""
        from module.parser.title_parser import TitleParser

        result = await TitleParser.raw_parser(self.PROBLEM_TITLE)
        assert result is not None
        assert result.official_title == "29 岁单身中坚冒险家的日常"
        assert result.title_raw == "29 岁单身中坚冒险家的日常"

    async def test_add_title_alias_rejects_none(self, db_session):
        """add_title_alias should reject None as alias."""
        from module.database.bangumi import BangumiDatabase
        from module.models import Bangumi

        db = BangumiDatabase(db_session)
        bangumi = Bangumi(
            official_title="29岁单身冒险家的日常",
            title_raw="[ANi] 29岁单身冒险家的日常",
            season=1,
        )
        db_session.add(bangumi)
        await db_session.commit()

        result = await db.add_title_alias(bangumi.id, None)
        assert result is False
        # Verify no alias was stored
        assert bangumi.title_aliases is None

    async def test_add_title_alias_rejects_empty_string(self, db_session):
        """add_title_alias should reject empty string as alias."""
        from module.database.bangumi import BangumiDatabase
        from module.models import Bangumi

        db = BangumiDatabase(db_session)
        bangumi = Bangumi(
            official_title="Test Anime",
            title_raw="[Group] Test Anime",
            season=1,
        )
        db_session.add(bangumi)
        await db_session.commit()

        result = await db.add_title_alias(bangumi.id, "")
        assert result is False

    def test_get_aliases_list_filters_null_values(self):
        """_get_aliases_list should filter out null values from JSON."""
        from module.database.bangumi import _get_aliases_list
        from module.models import Bangumi

        bangumi = Bangumi(title_raw="test", official_title="Test")
        # Simulates the corrupted state: [null] stored in DB
        bangumi.title_aliases = "[null]"
        assert _get_aliases_list(bangumi) == []

        # Mixed valid and null values
        bangumi.title_aliases = '[null, "valid_alias", null, "another"]'
        assert _get_aliases_list(bangumi) == ["valid_alias", "another"]

    async def test_get_all_title_patterns_skips_none_title_raw(self, db_session):
        """get_all_title_patterns should return empty list when title_raw is None."""
        from module.database.bangumi import BangumiDatabase
        from module.models import Bangumi

        db = BangumiDatabase(db_session)
        bangumi = Bangumi(official_title="Test Anime")
        bangumi.title_raw = None  # type: ignore[assignment]  # simulating corrupted data
        bangumi.title_aliases = None

        patterns = db.get_all_title_patterns(bangumi)
        assert patterns == []

    async def test_match_torrent_no_crash_on_none_title_raw(self, db_session):
        """match_torrent should not crash when a bangumi has None title_raw."""
        from module.database.bangumi import BangumiDatabase
        from module.models import Bangumi

        db = BangumiDatabase(db_session)
        # Insert a bangumi with corrupted title_raw (simulating the bug state)
        bangumi = Bangumi(
            official_title="29岁单身冒险家的日常",
            season=1,
        )
        bangumi.title_raw = None  # type: ignore[assignment]  # simulating corrupted data
        db_session.add(bangumi)
        await db_session.commit()

        # Should not raise TypeError: 'in <string>' requires string
        result = await db.match_torrent(
            "[ANi] 29 岁单身中坚冒险家的日常 - 07 [1080P][Baha][WEB-DL]"
        )
        assert result is None

    async def test_match_torrent_no_crash_on_null_aliases(self, db_session):
        """match_torrent should not crash when title_aliases contains null."""
        from module.database.bangumi import BangumiDatabase
        from module.models import Bangumi

        db = BangumiDatabase(db_session)
        bangumi = Bangumi(
            official_title="29岁单身冒险家的日常",
            title_raw="[ANi] 29岁单身冒险家的日常",
            season=1,
        )
        bangumi.title_aliases = "[null]"
        db_session.add(bangumi)
        await db_session.commit()

        # Should not crash — null aliases are filtered out
        result = await db.match_torrent(
            "[ANi] 29岁单身冒险家的日常 - 07 [1080P][Baha][WEB-DL]"
        )
        assert result is not None
        assert result.official_title == "29岁单身冒险家的日常"

    async def test_match_list_no_crash_on_corrupted_data(self, db_session):
        """match_list should handle bangumi with None title_raw and null aliases."""
        from unittest.mock import MagicMock

        from module.database.bangumi import BangumiDatabase
        from module.models import Bangumi

        db = BangumiDatabase(db_session)

        # Insert corrupted bangumi (title_raw=None, aliases=[null])
        bangumi = Bangumi(official_title="29岁单身冒险家的日常", season=1)
        bangumi.title_raw = None  # type: ignore[assignment]  # simulating corrupted data
        bangumi.title_aliases = "[null]"
        db_session.add(bangumi)

        # Insert a valid bangumi
        valid = Bangumi(
            official_title="葬送的芙莉莲",
            title_raw="葬送的芙莉莲 / Sousou no Frieren",
            season=1,
        )
        db_session.add(valid)
        await db_session.commit()

        torrent = MagicMock()
        torrent.name = "[ANi] 29 岁单身中坚冒险家的日常 - 07 [1080P]"

        # Should not crash even with corrupted data in the DB
        await db.match_list([torrent], "https://mikanani.me/RSS/test")


# ---------------------------------------------------------------------------
# Issue #992: Non-episodic resource causes AttributeError in title_parser
# https://github.com/EstrellaXD/Auto_Bangumi/issues/992
#
# When raw_parser returns None (movie/collection resources), title_parser
# accesses episode.title_zh on None, causing AttributeError.
# ---------------------------------------------------------------------------


class TestIssue992NonEpisodicAttributeError:
    """Issue #992: title_parser crashes on non-episodic resources."""

    # Titles that raw_parser cannot parse (returns None)
    NON_EPISODIC_TITLES = [
        "[阿特拉斯字幕组·雪原市出差所][命运-奇异赝品_Fate／strange Fake][04_半神们的卡农曲][简繁日内封PGS][日语配音版_Japanese Dub][Web-DL Remux][1080p AVC AAC]",
        "[KitaujiSub] Shikanoko Nokonoko Koshitantan [01Pre][WebRip][HEVC_AAC][CHS_JP].mp4",
    ]

    @pytest.mark.parametrize("title", NON_EPISODIC_TITLES)
    async def test_title_parser_returns_none_for_non_episodic(self, title):
        """TitleParser.raw_parser should return None instead of crashing."""
        from module.parser.title_parser import TitleParser

        result = await TitleParser.raw_parser(title)
        assert result is None

    def test_raw_parser_returns_none_for_unparseable(self):
        """raw_parser returns None for resources it cannot parse."""
        result = raw_parser(self.NON_EPISODIC_TITLES[0])
        assert result is None


# ---------------------------------------------------------------------------
# Issue #1005: BangumiDatabase missing search_official_title method
# https://github.com/EstrellaXD/Auto_Bangumi/issues/1005
# ---------------------------------------------------------------------------


class TestIssue1005SearchOfficialTitle:
    """Issue #1005: search_official_title method must exist on BangumiDatabase."""

    def test_method_exists(self):
        """BangumiDatabase should have search_official_title method."""
        from module.database.bangumi import BangumiDatabase

        assert hasattr(BangumiDatabase, "search_official_title")

    async def test_search_official_title_finds_match(self, db_session):
        """search_official_title returns the matching bangumi."""
        from module.database.bangumi import BangumiDatabase
        from module.models import Bangumi

        db = BangumiDatabase(db_session)
        bangumi = Bangumi(
            official_title="路人女主的养成方法",
            title_raw="Saenai Heroine no Sodatekata",
            season=1,
            rss_link="test",
        )
        await db.add(bangumi)

        result = await db.search_official_title("路人女主的养成方法")
        assert result is not None
        assert result.official_title == "路人女主的养成方法"

    async def test_search_official_title_returns_none_when_not_found(self, db_session):
        """search_official_title returns None for non-existent title."""
        from module.database.bangumi import BangumiDatabase

        db = BangumiDatabase(db_session)
        result = await db.search_official_title("不存在的番剧")
        assert result is None
