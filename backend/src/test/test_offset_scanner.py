"""Tests for OffsetScanner: real parsed-episode signal instead of a hardcoded guess."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from module.conf import settings
from module.core.offset_scanner import OffsetScanner
from module.database import Database
from module.models import Torrent
from module.notification.events import OffsetReviewEvent
from test.factories import make_bangumi

ISSUE_1072_TITLE = (
    "[SubsPlease] Haibara-kun no Tsuyokute Seishun New Game - 06v2 "
    "(1080p) [E931DD98].mkv"
)


class TestGetLatestParsedEpisode:
    """Tests for OffsetScanner._get_latest_parsed_episode."""

    @pytest.fixture(autouse=True)
    def use_preview_engine(self):
        with patch.object(settings.rss_parser, "engine", "tokenizer"):
            yield

    async def test_returns_none_when_no_torrents(self):
        scanner = OffsetScanner()
        assert await scanner._get_latest_parsed_episode(999) is None

    async def test_returns_max_parsed_episode_across_torrents(self):
        scanner = OffsetScanner()
        async with Database() as db:
            bangumi = make_bangumi(title_raw="Signal Anime Raw")
            await db.bangumi.add(bangumi)
            for ep in (1, 5, 3):
                await db.torrent.add(
                    Torrent(
                        name=f"[TestGroup] Signal Anime Raw - {ep:02d} [1080p].mkv",
                        url=f"https://example.com/{ep}",
                        refer_id=bangumi.id,
                    )
                )

        latest = await scanner._get_latest_parsed_episode(bangumi.id)
        assert latest == 5

    async def test_ignores_torrents_that_fail_to_parse(self):
        scanner = OffsetScanner()
        async with Database() as db:
            bangumi = make_bangumi(title_raw="Unparseable Anime Raw")
            await db.bangumi.add(bangumi)
            await db.torrent.add(
                Torrent(
                    name="this has no episode markers at all",
                    url="https://example.com/unparseable",
                    refer_id=bangumi.id,
                )
            )

        assert await scanner._get_latest_parsed_episode(bangumi.id) is None

    async def test_versioned_episode_is_used_instead_of_crc_token(self):
        scanner = OffsetScanner()
        async with Database() as db:
            bangumi = make_bangumi(title_raw="Issue 1072 Anime")
            await db.bangumi.add(bangumi)
            await db.torrent.add(
                Torrent(
                    name=ISSUE_1072_TITLE,
                    url="https://example.com/issue-1072",
                    refer_id=bangumi.id,
                )
            )

        assert await scanner._get_latest_parsed_episode(bangumi.id) == 6

    async def test_crc_without_episode_signal_is_ignored(self):
        scanner = OffsetScanner()
        async with Database() as db:
            bangumi = make_bangumi(title_raw="CRC Only Anime")
            await db.bangumi.add(bangumi)
            await db.torrent.add(
                Torrent(
                    name="[SubsPlease] CRC Only Anime (1080p) [E931DD98].mkv",
                    url="https://example.com/crc-only",
                    refer_id=bangumi.id,
                )
            )

        assert await scanner._get_latest_parsed_episode(bangumi.id) is None

    @pytest.mark.parametrize(
        "resource_name",
        [
            "[TestGroup] Signal Anime - 12.5 [1080p].mkv",
            "[TestGroup] Signal Anime Movie [1080p].mkv",
            "[TestGroup] Signal Anime OVA99 [1080p].mkv",
            "[TestGroup] Signal Anime OAD98 [1080p].mkv",
            "[TestGroup] Signal Anime SP97 [1080p].mkv",
            "[TestGroup] Signal Anime [01-99] [1080p].mkv",
            "[TestGroup] Signal Anime EP01 ~ EP99 [1080p].mkv",
            "[TestGroup] Signal Anime S02E01-E99 [1080p].mkv",
            "[TestGroup] Signal Anime OVA01-99 [1080p].mkv",
            "[TestGroup] Signal Anime Complete Batch [1080p].mkv",
            "[TestGroup] Signal Anime 合集 [1080p].mkv",
            "[TestGroup] Signal Anime [TV 01-12 + OVA 01-02] [1080p].mkv",
            "[TestGroup] Signal Anime PV99 [1080p].mkv",
            "[TestGroup] Signal Anime [1080p].mkv",
        ],
        ids=[
            "fractional",
            "movie",
            "ova",
            "oad",
            "special",
            "range",
            "spaced-explicit-range",
            "season-range",
            "ova-range",
            "batch",
            "collection",
            "mixed-collection",
            "pv",
            "title-only",
        ],
    )
    async def test_non_weekly_resources_are_not_offset_signals(self, resource_name):
        scanner = OffsetScanner()
        async with Database() as db:
            bangumi = make_bangumi(title_raw="Signal Anime")
            await db.bangumi.add(bangumi)
            await db.torrent.add(
                Torrent(
                    name=resource_name,
                    url="https://example.com/non-weekly",
                    refer_id=bangumi.id,
                )
            )

        assert await scanner._get_latest_parsed_episode(bangumi.id) is None

    async def test_offset_signal_follows_selected_parser_engine(self):
        scanner = OffsetScanner()
        async with Database() as db:
            bangumi = make_bangumi(title_raw="Signal Anime")
            await db.bangumi.add(bangumi)
            await db.torrent.add(
                Torrent(
                    name="[TestGroup] Signal Anime EP01 ~ EP02 [1080p].mkv",
                    url="https://example.com/configured-range",
                    refer_id=bangumi.id,
                )
            )

        with patch.object(settings.rss_parser, "engine", "classic"):
            classic = await scanner._get_latest_parsed_episode(bangumi.id)
        with patch.object(settings.rss_parser, "engine", "tokenizer"):
            preview = await scanner._get_latest_parsed_episode(bangumi.id)

        assert classic == 2
        assert preview is None

    async def test_excluded_resources_do_not_override_latest_weekly_episode(self):
        scanner = OffsetScanner()
        resource_names = [
            "[TestGroup] Signal Anime - 05 [1080p].mkv",
            "[TestGroup] Signal Anime - 99.5 [1080p].mkv",
            "[TestGroup] Signal Anime Movie [1080p].mkv",
            "[TestGroup] Signal Anime OVA99 [1080p].mkv",
            "[TestGroup] Signal Anime OAD98 [1080p].mkv",
            "[TestGroup] Signal Anime SP97 [1080p].mkv",
            "[TestGroup] Signal Anime [01-100] [1080p].mkv",
            "[TestGroup] Signal Anime EP01 ~ EP100 [1080p].mkv",
            "[TestGroup] Signal Anime S02E01-E100 [1080p].mkv",
            "[TestGroup] Signal Anime OVA01-100 [1080p].mkv",
            "[TestGroup] Signal Anime Complete Batch [1080p].mkv",
            "[TestGroup] Signal Anime 合集 [1080p].mkv",
            "[TestGroup] Signal Anime [TV 01-12 + OVA 01-02] [1080p].mkv",
            "[TestGroup] Signal Anime PV99 [1080p].mkv",
            "[TestGroup] Signal Anime [1080p].mkv",
        ]
        async with Database() as db:
            bangumi = make_bangumi(title_raw="Signal Anime")
            await db.bangumi.add(bangumi)
            for index, resource_name in enumerate(resource_names):
                await db.torrent.add(
                    Torrent(
                        name=resource_name,
                        url=f"https://example.com/mixed/{index}",
                        refer_id=bangumi.id,
                    )
                )

        assert await scanner._get_latest_parsed_episode(bangumi.id) == 5

    async def test_versioned_weekly_episode_remains_an_offset_signal(self):
        scanner = OffsetScanner()
        async with Database() as db:
            bangumi = make_bangumi(title_raw="Signal Anime")
            await db.bangumi.add(bangumi)
            await db.torrent.add(
                Torrent(
                    name="[TestGroup] Signal Anime - 12v2 [1080p].mkv",
                    url="https://example.com/versioned",
                    refer_id=bangumi.id,
                )
            )

        assert await scanner._get_latest_parsed_episode(bangumi.id) == 12


class TestCheckBangumiUsesRealSignal:
    """Tests for OffsetScanner._check_bangumi consuming the real torrent signal."""

    @staticmethod
    def _ended_twelve_episode_season():
        info = MagicMock()
        info.last_season = 1
        info.season_episode_counts = {1: 12}
        info.series_status = "Ended"
        info.virtual_season_starts = None
        return info

    async def test_skips_when_no_torrent_signal(self):
        """No torrent records for the bangumi means no real signal: never flag."""
        scanner = OffsetScanner()
        bangumi = make_bangumi(id=1, season=2, season_offset=0, episode_offset=0)

        with patch(
            "module.core.offset_scanner.tmdb_parser",
            new=AsyncMock(return_value=MagicMock(last_season=1)),
        ):
            event = await scanner._check_bangumi(bangumi)

        assert event is None

    @pytest.mark.parametrize("episode_type", ("special", "movie"))
    async def test_skips_non_episode_bangumi_before_tmdb_lookup(
        self, episode_type: str
    ):
        scanner = OffsetScanner()
        bangumi = make_bangumi(
            id=1,
            episode_type=episode_type,
            season_offset=0,
            episode_offset=0,
        )

        with patch(
            "module.core.offset_scanner.tmdb_parser", new_callable=AsyncMock
        ) as mock_tmdb:
            event = await scanner._check_bangumi(bangumi)

        assert event is None
        mock_tmdb.assert_not_awaited()

    async def test_flags_using_real_latest_episode_from_torrent_table(self):
        """A mismatch is only suggested from the actual parsed episode, not a constant."""
        scanner = OffsetScanner()
        async with Database() as db:
            bangumi = make_bangumi(
                title_raw="Signal Anime Raw 2",
                season=2,
                season_offset=0,
                episode_offset=0,
            )
            await db.bangumi.add(bangumi)
            await db.torrent.add(
                Torrent(
                    name="[TestGroup] Signal Anime Raw 2 - 25 [1080p].mkv",
                    url="https://example.com/25",
                    refer_id=bangumi.id,
                )
            )

        fake_tmdb_info = MagicMock()
        fake_tmdb_info.last_season = 1
        fake_tmdb_info.season_episode_counts = {1: 24}
        fake_tmdb_info.series_status = "Ended"
        fake_tmdb_info.virtual_season_starts = None

        with patch(
            "module.core.offset_scanner.tmdb_parser",
            new=AsyncMock(return_value=fake_tmdb_info),
        ):
            event = await scanner._check_bangumi(bangumi)

        assert isinstance(event, OffsetReviewEvent)
        assert event.official_title == bangumi.official_title

        async with Database() as db:
            updated = await db.bangumi.search_id(bangumi.id)
        assert updated.needs_review is True
        assert updated.suggested_season_offset == -1

    async def test_versioned_episode_with_crc_does_not_create_false_review(self):
        scanner = OffsetScanner()
        async with Database() as db:
            bangumi = make_bangumi(
                title_raw="Issue 1072 Anime",
                season=1,
                season_offset=0,
                episode_offset=0,
            )
            await db.bangumi.add(bangumi)
            await db.torrent.add(
                Torrent(
                    name=ISSUE_1072_TITLE,
                    url="https://example.com/issue-1072-review",
                    refer_id=bangumi.id,
                )
            )

        with patch(
            "module.core.offset_scanner.tmdb_parser",
            new=AsyncMock(return_value=self._ended_twelve_episode_season()),
        ):
            event = await scanner._check_bangumi(bangumi)

        assert event is None
        async with Database() as db:
            updated = await db.bangumi.search_id(bangumi.id)
        assert updated.needs_review is False
        assert updated.needs_review_reason is None
        assert updated.suggested_season_offset is None
        assert updated.suggested_episode_offset is None

    async def test_real_episode_thirteen_still_creates_review(self):
        scanner = OffsetScanner()
        async with Database() as db:
            bangumi = make_bangumi(
                title_raw="Episode Overflow Anime",
                season=1,
                season_offset=0,
                episode_offset=0,
            )
            await db.bangumi.add(bangumi)
            await db.torrent.add(
                Torrent(
                    name="[SubsPlease] Episode Overflow Anime E13 [1080p].mkv",
                    url="https://example.com/episode-13",
                    refer_id=bangumi.id,
                )
            )

        with patch(
            "module.core.offset_scanner.tmdb_parser",
            new=AsyncMock(return_value=self._ended_twelve_episode_season()),
        ):
            event = await scanner._check_bangumi(bangumi)

        assert isinstance(event, OffsetReviewEvent)
        async with Database() as db:
            updated = await db.bangumi.search_id(bangumi.id)
        assert updated.needs_review is True
        assert updated.needs_review_reason is not None
        assert "13" in updated.needs_review_reason
        assert "12" in updated.needs_review_reason

    @pytest.mark.parametrize(
        ("season", "episode", "kept_after_catch_up"),
        [
            (1, 13, True),  # 只超出集数：TMDB 跟上后也不自动清除，由用户处理
            (2, 5, False),  # 季度对不上：TMDB 跟上后不再不匹配，自动清除
        ],
        ids=["overflow-only", "season-mismatch"],
    )
    async def test_airing_show_flag_notifies_once(
        self, season, episode, kept_after_catch_up
    ):
        """连载中的番剧标记后只通知一次；只超出集数的标记不随复扫清除（#1072）。"""
        scanner = OffsetScanner()
        async with Database() as db:
            bangumi = make_bangumi(
                title_raw="Airing Anime",
                season=season,
                season_offset=0,
                episode_offset=0,
            )
            await db.bangumi.add(bangumi)
            await db.torrent.add(
                Torrent(
                    name=f"[TestGroup] Airing Anime - {episode:02d} [1080p].mkv",
                    url="https://example.com/airing",
                    refer_id=bangumi.id,
                )
            )

        tmdb_info = self._ended_twelve_episode_season()
        tmdb_info.series_status = "Returning Series"

        async def scan():
            async with Database() as db:
                current = await db.bangumi.search_id(bangumi.id)
            with patch(
                "module.core.offset_scanner.tmdb_parser",
                new=AsyncMock(return_value=tmdb_info),
            ):
                event = await scanner._check_bangumi(current)
            async with Database() as db:
                updated = await db.bangumi.search_id(bangumi.id)
            return event, updated.needs_review

        # 首次扫描：标记并通知一次
        event, needs_review = await scan()
        assert isinstance(event, OffsetReviewEvent)
        assert needs_review is True

        # 复扫仍是同样的不匹配：保留标记，不再通知
        assert await scan() == (None, True)

        # TMDB 跟上（多了第 13 集和第 2 季）后复扫：不再通知
        tmdb_info.last_season = 2
        tmdb_info.season_episode_counts = {1: 13, 2: 12}
        assert await scan() == (None, kept_after_catch_up)


class TestRescanFlaggedBangumi:
    """已标记的番剧重新扫描：误报自动清除，其余情况保留标记（#1072）。"""

    @pytest.mark.parametrize(
        ("episode", "season_offset", "tmdb_found", "expected_reason"),
        [
            (6, 0, True, None),  # TMDB 已更新 / 解析已修正：不再不匹配，清除
            (13, 0, True, "调整后集数13超出TMDB该季的12集"),  # 仍不匹配：换成新原因
            (6, -1, True, "旧原因"),  # 用户已手动配置偏移：不动
            (6, 0, False, "旧原因"),  # TMDB 暂时查不到：没有新结论，不动
        ],
        ids=["no-mismatch", "still-mismatch", "user-offset", "tmdb-miss"],
    )
    async def test_rescan_clears_only_stale_scanner_flag(
        self, episode, season_offset, tmdb_found, expected_reason
    ):
        scanner = OffsetScanner()
        reason = "旧原因"
        async with Database() as db:
            bangumi = make_bangumi(
                title_raw="Rescan Anime",
                season=1,
                season_offset=season_offset,
                episode_offset=0,
            )
            await db.bangumi.add(bangumi)
            # 建议偏移非 0 的真实不匹配标记；只超出集数的标记不自动清除
            await db.bangumi.set_needs_review(
                bangumi.id, reason, suggested_season_offset=-1
            )
            await db.torrent.add(
                Torrent(
                    name=f"[TestGroup] Rescan Anime - {episode:02d} [1080p].mkv",
                    url="https://example.com/rescan",
                    refer_id=bangumi.id,
                )
            )
            bangumi = await db.bangumi.search_id(bangumi.id)

        tmdb_info = TestCheckBangumiUsesRealSignal._ended_twelve_episode_season()
        with patch(
            "module.core.offset_scanner.tmdb_parser",
            new=AsyncMock(return_value=tmdb_info if tmdb_found else None),
        ):
            event = await scanner._check_bangumi(bangumi)

        # 已标记过的番剧不再重复发送检查通知
        assert event is None
        async with Database() as db:
            updated = await db.bangumi.search_id(bangumi.id)
        assert updated.needs_review is (expected_reason is not None)
        assert updated.needs_review_reason == expected_reason
