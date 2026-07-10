"""Tests for OffsetScanner: real parsed-episode signal instead of a hardcoded guess."""

from unittest.mock import AsyncMock, MagicMock, patch

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
                        bangumi_id=bangumi.id,
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
                    bangumi_id=bangumi.id,
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
                    bangumi_id=bangumi.id,
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
                    bangumi_id=bangumi.id,
                )
            )

        assert await scanner._get_latest_parsed_episode(bangumi.id) is None


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
                    bangumi_id=bangumi.id,
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
                    bangumi_id=bangumi.id,
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
                    bangumi_id=bangumi.id,
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
