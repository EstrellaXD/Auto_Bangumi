"""Tests for RSS engine: pull_rss, match_torrent, refresh_rss, add_rss."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from module.database import Database
from module.downloader import AddResult
from module.models import Torrent
from module.notification.events import DownloadFailureEvent, RssFailureEvent
from module.rss.engine import RSSEngine
from test.factories import make_bangumi, make_rss_item, make_torrent


@pytest_asyncio.fixture
async def rss_engine(db_engine):
    """RSSEngine backed by in-memory database."""
    return RSSEngine(Database(engine=db_engine))


# ---------------------------------------------------------------------------
# pull_rss
# ---------------------------------------------------------------------------


class TestPullRss:
    async def test_returns_only_new_torrents(self, rss_engine):
        """pull_rss filters out torrents already in the database."""
        rss_item = make_rss_item()
        await rss_engine.db.rss.add(rss_item)
        rss_item = await rss_engine.db.rss.search_id(1)

        # Pre-insert one torrent into DB
        existing = make_torrent(url="https://example.com/existing.torrent", rss_id=1)
        await rss_engine.db.torrent.add(existing)

        # Mock _get_torrents to return 3 torrents (1 existing + 2 new)
        all_torrents = [
            Torrent(name="existing", url="https://example.com/existing.torrent"),
            Torrent(name="new1", url="https://example.com/new1.torrent"),
            Torrent(name="new2", url="https://example.com/new2.torrent"),
        ]
        with patch.object(
            RSSEngine, "_get_torrents", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = all_torrents
            result = await rss_engine.pull_rss(rss_item)

        assert len(result) == 2
        assert all(t.url != "https://example.com/existing.torrent" for t in result)

    async def test_all_existing_returns_empty(self, rss_engine):
        """When all torrents already exist, returns empty list."""
        rss_item = make_rss_item()
        await rss_engine.db.rss.add(rss_item)
        rss_item = await rss_engine.db.rss.search_id(1)

        existing = make_torrent(url="https://example.com/only.torrent", rss_id=1)
        await rss_engine.db.torrent.add(existing)

        with patch.object(
            RSSEngine, "_get_torrents", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [
                Torrent(name="only", url="https://example.com/only.torrent")
            ]
            result = await rss_engine.pull_rss(rss_item)

        assert result == []

    async def test_empty_feed_returns_empty(self, rss_engine):
        """When RSS feed has no torrents, returns empty list."""
        rss_item = make_rss_item()
        await rss_engine.db.rss.add(rss_item)
        rss_item = await rss_engine.db.rss.search_id(1)

        with patch.object(
            RSSEngine, "_get_torrents", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = []
            result = await rss_engine.pull_rss(rss_item)

        assert result == []


# ---------------------------------------------------------------------------
# match_torrent
# ---------------------------------------------------------------------------


class TestMatchTorrent:
    async def test_matches_by_title_raw_substring(self, rss_engine):
        """match_torrent finds Bangumi when title_raw is a substring of torrent name."""
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="")
        await rss_engine.db.bangumi.add(bangumi)

        torrent = make_torrent(name="[Lilith-Raws] Mushoku Tensei - 11 [1080p].mkv")
        result = rss_engine.match_torrent(
            torrent, await rss_engine.db.bangumi.search_all()
        )

        assert result is not None
        assert result.title_raw == "Mushoku Tensei"

    async def test_no_match_returns_none(self, rss_engine):
        """Returns None when no Bangumi matches the torrent name."""
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="")
        await rss_engine.db.bangumi.add(bangumi)

        torrent = make_torrent(name="[Sub] Completely Different Anime - 01.mkv")
        result = rss_engine.match_torrent(
            torrent, await rss_engine.db.bangumi.search_all()
        )

        assert result is None

    async def test_filter_excludes_matching_torrent(self, rss_engine):
        """When torrent name matches the filter regex, returns None."""
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="720")
        await rss_engine.db.bangumi.add(bangumi)

        torrent = make_torrent(name="[Sub] Mushoku Tensei - 01 [720p].mkv")
        result = rss_engine.match_torrent(
            torrent, await rss_engine.db.bangumi.search_all()
        )

        assert result is None

    async def test_empty_filter_allows_match(self, rss_engine):
        """When filter is empty string, all matching torrents pass."""
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="")
        await rss_engine.db.bangumi.add(bangumi)

        torrent = make_torrent(name="[Sub] Mushoku Tensei - 01 [720p].mkv")
        result = rss_engine.match_torrent(
            torrent, await rss_engine.db.bangumi.search_all()
        )

        assert result is not None

    async def test_filter_case_insensitive(self, rss_engine):
        """Filter regex matching is case-insensitive."""
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="HEVC")
        await rss_engine.db.bangumi.add(bangumi)

        # Torrent has "hevc" in lowercase - should still be filtered
        torrent = make_torrent(name="[Sub] Mushoku Tensei - 01 [1080p][hevc].mkv")
        result = rss_engine.match_torrent(
            torrent, await rss_engine.db.bangumi.search_all()
        )

        assert result is None

    async def test_deleted_bangumi_not_matched(self, rss_engine):
        """Bangumi with deleted=True should not match."""
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="", deleted=True)
        await rss_engine.db.bangumi.add(bangumi)

        torrent = make_torrent(name="[Sub] Mushoku Tensei - 01 [1080p].mkv")
        result = rss_engine.match_torrent(
            torrent, await rss_engine.db.bangumi.search_all()
        )

        assert result is None

    async def test_comma_separated_filters(self, rss_engine):
        """Multiple comma-separated filters are joined with | for OR matching."""
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="720,480")
        await rss_engine.db.bangumi.add(bangumi)

        # Matches one of the filters
        torrent = make_torrent(name="[Sub] Mushoku Tensei - 01 [480p].mkv")
        result = rss_engine.match_torrent(
            torrent, await rss_engine.db.bangumi.search_all()
        )

        assert result is None

        # Doesn't match any filter
        torrent2 = make_torrent(name="[Sub] Mushoku Tensei - 01 [1080p].mkv")
        result2 = rss_engine.match_torrent(
            torrent2, await rss_engine.db.bangumi.search_all()
        )

        assert result2 is not None

    async def test_match_torrent_filter_rejected_leaves_bangumi_id_unset(
        self, rss_engine
    ):
        """A filter-rejected torrent must NOT be associated with the bangumi,
        or OffsetScanner would compute offsets from excluded episodes."""
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="720")
        await rss_engine.db.bangumi.add(bangumi)

        torrent = make_torrent(name="[Sub] Mushoku Tensei - 01 [720p].mkv")
        result = rss_engine.match_torrent(
            torrent, await rss_engine.db.bangumi.search_all()
        )

        assert result is None
        assert torrent.bangumi_id is None

    async def test_match_torrent_filter_passed_sets_bangumi_id(self, rss_engine):
        """A torrent passing a non-empty filter gets bangumi_id set."""
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="720")
        await rss_engine.db.bangumi.add(bangumi)

        torrent = make_torrent(name="[Sub] Mushoku Tensei - 01 [1080p].mkv")
        result = rss_engine.match_torrent(
            torrent, await rss_engine.db.bangumi.search_all()
        )

        assert result is not None
        assert torrent.bangumi_id == result.id

    async def test_match_torrent_empty_filter_sets_bangumi_id(self, rss_engine):
        """A torrent matched with an empty filter also gets bangumi_id set."""
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="")
        await rss_engine.db.bangumi.add(bangumi)

        torrent = make_torrent(name="[Sub] Mushoku Tensei - 01 [1080p].mkv")
        result = rss_engine.match_torrent(
            torrent, await rss_engine.db.bangumi.search_all()
        )

        assert result is not None
        assert torrent.bangumi_id == result.id


# ---------------------------------------------------------------------------
# refresh_rss
# ---------------------------------------------------------------------------


class TestRefreshRss:
    async def test_downloads_matched_torrents(self, rss_engine, mock_qb_client):
        """refresh_rss downloads torrents that match a bangumi rule."""
        # Setup DB
        rss_item = make_rss_item(enabled=True)
        await rss_engine.db.rss.add(rss_item)
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="")
        await rss_engine.db.bangumi.add(bangumi)

        # Mock network
        new_torrent = Torrent(
            name="[Sub] Mushoku Tensei - 12 [1080p].mkv",
            url="https://example.com/ep12.torrent",
        )
        with patch.object(
            RSSEngine, "_get_torrents", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [new_torrent]

            # Create a mock client
            client = AsyncMock()
            client.add_torrent = AsyncMock(return_value=AddResult.ADDED)

            await rss_engine.refresh_rss(client)

        # Verify download was attempted
        client.add_torrent.assert_called_once()
        # Verify torrent stored in DB
        all_torrents = await rss_engine.db.torrent.search_all()
        assert len(all_torrents) == 1
        assert all_torrents[0].downloaded is True

    async def test_unmatched_torrents_stored_not_downloaded(self, rss_engine):
        """Unmatched torrents are stored in DB but not marked downloaded."""
        rss_item = make_rss_item(enabled=True)
        await rss_engine.db.rss.add(rss_item)
        # No bangumi in DB to match

        unmatched = Torrent(
            name="[Sub] Unknown Anime - 01 [1080p].mkv",
            url="https://example.com/unknown.torrent",
        )
        with patch.object(
            RSSEngine, "_get_torrents", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [unmatched]
            client = AsyncMock()
            await rss_engine.refresh_rss(client)

        client.add_torrent.assert_not_called()
        all_torrents = await rss_engine.db.torrent.search_all()
        assert len(all_torrents) == 1
        assert all_torrents[0].downloaded is False

    async def test_track_orphans_off_skips_unmatched_persist(
        self, rss_engine, test_settings
    ):
        """关闭 track_orphans 后未匹配种子不再入库；匹配的照常入库。"""
        test_settings.bangumi_manage.track_orphans = False
        rss_item = make_rss_item(enabled=True)
        await rss_engine.db.rss.add(rss_item)
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="")
        await rss_engine.db.bangumi.add(bangumi)

        matched = Torrent(
            name="[Sub] Mushoku Tensei - 12 [1080p].mkv",
            url="https://example.com/ep12.torrent",
        )
        unmatched = Torrent(
            name="[Sub] Unknown Anime - 01 [1080p].mkv",
            url="https://example.com/unknown.torrent",
        )
        with (
            patch.object(
                RSSEngine, "_get_torrents", new_callable=AsyncMock
            ) as mock_get,
            # conftest 的 mock_settings 补丁的是 module.conf.settings，
            # 不会重绑 engine 模块内的名字——必须补丁消费方模块
            patch("module.rss.engine.settings", test_settings),
        ):
            mock_get.return_value = [matched, unmatched]
            client = AsyncMock()
            client.add_torrent = AsyncMock(return_value=AddResult.ADDED)
            await rss_engine.refresh_rss(client)

        all_torrents = await rss_engine.db.torrent.search_all()
        assert len(all_torrents) == 1
        assert all_torrents[0].bangumi_id is not None

    async def test_track_orphans_on_persists_unmatched(
        self, rss_engine, test_settings
    ):
        """默认开启时行为不变：未匹配种子以 bangumi_id NULL 入库。"""
        rss_item = make_rss_item(enabled=True)
        await rss_engine.db.rss.add(rss_item)
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="")
        await rss_engine.db.bangumi.add(bangumi)

        matched = Torrent(
            name="[Sub] Mushoku Tensei - 12 [1080p].mkv",
            url="https://example.com/ep12.torrent",
        )
        unmatched = Torrent(
            name="[Sub] Unknown Anime - 01 [1080p].mkv",
            url="https://example.com/unknown.torrent",
        )
        with (
            patch.object(
                RSSEngine, "_get_torrents", new_callable=AsyncMock
            ) as mock_get,
            # 同样补丁 engine 的 settings，避免开发机 config_dev.json 干扰
            patch("module.rss.engine.settings", test_settings),
        ):
            mock_get.return_value = [matched, unmatched]
            client = AsyncMock()
            client.add_torrent = AsyncMock(return_value=AddResult.ADDED)
            await rss_engine.refresh_rss(client)

        all_torrents = await rss_engine.db.torrent.search_all()
        assert len(all_torrents) == 2
        assert any(t.bangumi_id is None for t in all_torrents)

    async def test_refresh_specific_rss_id(self, rss_engine):
        """refresh_rss with rss_id only processes that specific feed."""
        rss1 = make_rss_item(name="Feed 1", url="https://feed1.com/rss")
        rss2 = make_rss_item(name="Feed 2", url="https://feed2.com/rss")
        await rss_engine.db.rss.add(rss1)
        await rss_engine.db.rss.add(rss2)

        with patch.object(
            RSSEngine, "_get_torrents", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = []
            client = AsyncMock()
            await rss_engine.refresh_rss(client, rss_id=2)

        # Only called once (for rss_id=2)
        mock_get.assert_called_once()

    async def test_refresh_nonexistent_rss_id(self, rss_engine):
        """refresh_rss with non-existent rss_id does nothing."""
        with patch.object(
            RSSEngine, "_get_torrents", new_callable=AsyncMock
        ) as mock_get:
            client = AsyncMock()
            await rss_engine.refresh_rss(client, rss_id=999)

        mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# refresh_rss notification events (RSS failure transition, download failure)
# ---------------------------------------------------------------------------


class TestRefreshRssEvents:
    async def test_healthy_to_error_transition_returns_rss_failure_event(
        self, rss_engine
    ):
        """A feed going from healthy to error is reported exactly once."""
        rss_item = make_rss_item(
            name="Feed 1", url="https://feed1.example/rss", enabled=True
        )
        await rss_engine.db.rss.add(rss_item)

        with patch.object(
            RSSEngine, "_pull_rss_with_status", new_callable=AsyncMock
        ) as mock_pull:
            mock_pull.return_value = ([], "connection refused")
            client = AsyncMock()
            events = await rss_engine.refresh_rss(client)

        assert len(events) == 1
        assert isinstance(events[0], RssFailureEvent)
        assert events[0].rss_name == "Feed 1"
        assert events[0].error == "connection refused"

    async def test_error_stays_error_does_not_repeat_event(self, rss_engine):
        """A feed already in 'error' does not re-fire on every subsequent tick."""
        rss_item = make_rss_item(url="https://feed1.example/rss", enabled=True)
        await rss_engine.db.rss.add(rss_item)

        with patch.object(
            RSSEngine, "_pull_rss_with_status", new_callable=AsyncMock
        ) as mock_pull:
            mock_pull.return_value = ([], "connection refused")
            client = AsyncMock()
            first_events = await rss_engine.refresh_rss(client)
            second_events = await rss_engine.refresh_rss(client)

        assert len(first_events) == 1
        assert second_events == []

    async def test_no_error_returns_no_rss_failure_event(self, rss_engine):
        """A healthy feed produces no failure event."""
        rss_item = make_rss_item(url="https://feed1.example/rss", enabled=True)
        await rss_engine.db.rss.add(rss_item)

        with patch.object(
            RSSEngine, "_pull_rss_with_status", new_callable=AsyncMock
        ) as mock_pull:
            mock_pull.return_value = ([], None)
            client = AsyncMock()
            events = await rss_engine.refresh_rss(client)

        assert events == []

    async def test_add_torrent_failure_returns_download_failure_event(self, rss_engine):
        """A matched torrent that fails to add is reported as a download failure."""
        rss_item = make_rss_item(enabled=True)
        await rss_engine.db.rss.add(rss_item)
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="")
        await rss_engine.db.bangumi.add(bangumi)

        new_torrent = Torrent(
            name="[Sub] Mushoku Tensei - 12 [1080p].mkv",
            url="https://example.com/ep12.torrent",
        )
        with patch.object(
            RSSEngine, "_get_torrents", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [new_torrent]
            client = AsyncMock()
            client.add_torrent = AsyncMock(return_value=AddResult.FAILED)

            events = await rss_engine.refresh_rss(client)

        assert len(events) == 1
        assert isinstance(events[0], DownloadFailureEvent)
        assert events[0].official_title == bangumi.official_title
        assert events[0].torrent_name == new_torrent.name

        # The failed torrent is NOT persisted, so a later tick can retry it.
        all_torrents = await rss_engine.db.torrent.search_all()
        assert all_torrents == []

    async def test_add_torrent_success_returns_no_download_failure_event(
        self, rss_engine, mock_qb_client
    ):
        """A torrent that adds successfully produces no failure event."""
        rss_item = make_rss_item(enabled=True)
        await rss_engine.db.rss.add(rss_item)
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="")
        await rss_engine.db.bangumi.add(bangumi)

        new_torrent = Torrent(
            name="[Sub] Mushoku Tensei - 12 [1080p].mkv",
            url="https://example.com/ep12.torrent",
        )
        with patch.object(
            RSSEngine, "_get_torrents", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [new_torrent]
            client = AsyncMock()
            client.add_torrent = AsyncMock(return_value=AddResult.ADDED)

            events = await rss_engine.refresh_rss(client)

        assert events == []

    async def test_add_torrent_duplicate_marks_downloaded_without_event(
        self, rss_engine
    ):
        """A torrent the client already has (DUPLICATE) is treated as success:
        no failure notification, row persisted as downloaded."""
        rss_item = make_rss_item(enabled=True)
        await rss_engine.db.rss.add(rss_item)
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="")
        await rss_engine.db.bangumi.add(bangumi)

        new_torrent = Torrent(
            name="[Sub] Mushoku Tensei - 12 [1080p].mkv",
            url="https://example.com/ep12.torrent",
        )
        with patch.object(
            RSSEngine, "_get_torrents", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [new_torrent]
            client = AsyncMock()
            client.add_torrent = AsyncMock(return_value=AddResult.DUPLICATE)

            events = await rss_engine.refresh_rss(client)

        assert events == []
        all_torrents = await rss_engine.db.torrent.search_all()
        assert len(all_torrents) == 1
        assert all_torrents[0].downloaded is True


# ---------------------------------------------------------------------------
# refresh_rss retry semantics for failed adds
# ---------------------------------------------------------------------------


class TestRefreshRssRetry:
    async def test_refresh_rss_failed_add_retried_on_next_tick(self, rss_engine):
        """A torrent whose add FAILED is re-attempted on the next refresh
        (it must not be persisted, or check_new would filter it forever)."""
        rss_item = make_rss_item(enabled=True)
        await rss_engine.db.rss.add(rss_item)
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="")
        await rss_engine.db.bangumi.add(bangumi)

        def feed_torrent():
            return Torrent(
                name="[Sub] Mushoku Tensei - 12 [1080p].mkv",
                url="https://example.com/ep12.torrent",
            )

        with patch.object(
            RSSEngine, "_get_torrents", new_callable=AsyncMock
        ) as mock_get:
            client = AsyncMock()

            # Tick 1: transient failure
            mock_get.return_value = [feed_torrent()]
            client.add_torrent = AsyncMock(return_value=AddResult.FAILED)
            await rss_engine.refresh_rss(client)
            client.add_torrent.assert_called_once()
            assert await rss_engine.db.torrent.search_all() == []

            # Tick 2: same feed item is still there, add now succeeds
            mock_get.return_value = [feed_torrent()]
            client.add_torrent = AsyncMock(return_value=AddResult.ADDED)
            await rss_engine.refresh_rss(client)
            client.add_torrent.assert_called_once()

        all_torrents = await rss_engine.db.torrent.search_all()
        assert len(all_torrents) == 1
        assert all_torrents[0].downloaded is True

    async def test_refresh_rss_filter_rejected_persisted_and_not_retried(
        self, rss_engine
    ):
        """Filter-rejected torrents keep the old behavior: persisted once
        (downloaded=False, no bangumi association) and never re-processed."""
        rss_item = make_rss_item(enabled=True)
        await rss_engine.db.rss.add(rss_item)
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="720")
        await rss_engine.db.bangumi.add(bangumi)

        def feed_torrent():
            return Torrent(
                name="[Sub] Mushoku Tensei - 01 [720p].mkv",
                url="https://example.com/ep01-720.torrent",
            )

        with patch.object(
            RSSEngine, "_get_torrents", new_callable=AsyncMock
        ) as mock_get:
            client = AsyncMock()
            client.add_torrent = AsyncMock(return_value=AddResult.ADDED)

            mock_get.return_value = [feed_torrent()]
            await rss_engine.refresh_rss(client)
            mock_get.return_value = [feed_torrent()]
            await rss_engine.refresh_rss(client)

        client.add_torrent.assert_not_called()
        all_torrents = await rss_engine.db.torrent.search_all()
        assert len(all_torrents) == 1
        assert all_torrents[0].downloaded is False
        assert all_torrents[0].bangumi_id is None


class TestDownloadBangumi:
    async def test_success_persists_torrents_with_bangumi_id(self, rss_engine):
        """成功下载后种子行必须关联 bangumi_id，否则会被记成孤儿。"""
        bangumi = make_bangumi(
            official_title="Mushoku Tensei",
            rss_link="https://example.com/rss",
            filter="",
        )
        await rss_engine.db.bangumi.add(bangumi)
        torrent = Torrent(
            name="[Sub] Mushoku Tensei - 12 [1080p].mkv",
            url="https://example.com/ep12.torrent",
        )
        with (
            patch("module.rss.engine.RequestContent") as MockReq,
            patch("module.rss.engine.DownloadClient") as MockClient,
        ):
            req = AsyncMock()
            req.get_torrents = AsyncMock(return_value=[torrent])
            MockReq.return_value.__aenter__ = AsyncMock(return_value=req)
            MockReq.return_value.__aexit__ = AsyncMock(return_value=False)
            client = AsyncMock()
            client.add_torrent = AsyncMock(return_value=AddResult.ADDED)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = await rss_engine.download_bangumi(bangumi)

        assert resp.status is True
        stored = await rss_engine.db.torrent.search_all()
        assert len(stored) == 1
        assert stored[0].bangumi_id == bangumi.id

    async def test_failed_add_returns_failure_and_does_not_persist(self, rss_engine):
        bangumi = make_bangumi(
            official_title="Mushoku Tensei",
            rss_link="https://example.com/rss",
            filter="",
        )
        torrent = Torrent(
            name="[Sub] Mushoku Tensei - 12 [1080p].mkv",
            url="https://example.com/ep12.torrent",
        )
        with (
            patch("module.rss.engine.RequestContent") as MockReq,
            patch("module.rss.engine.DownloadClient") as MockClient,
        ):
            req = AsyncMock()
            req.get_torrents = AsyncMock(return_value=[torrent])
            MockReq.return_value.__aenter__ = AsyncMock(return_value=req)
            MockReq.return_value.__aexit__ = AsyncMock(return_value=False)
            client = AsyncMock()
            client.add_torrent = AsyncMock(return_value=AddResult.FAILED)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = await rss_engine.download_bangumi(bangumi)

        assert resp.status is False
        assert resp.status_code == 502
        assert await rss_engine.db.torrent.search_all() == []


# ---------------------------------------------------------------------------
# add_rss
# ---------------------------------------------------------------------------


class TestAddRss:
    async def test_add_with_name(self, rss_engine):
        """add_rss with explicit name skips HTTP fetch and creates record."""
        result = await rss_engine.add_rss(
            rss_link="https://mikanani.me/RSS/test",
            name="My Feed",
            aggregate=True,
            parser="mikan",
        )

        assert result.status is True
        assert result.status_code == 200
        rss = await rss_engine.db.rss.search_id(1)
        assert rss.name == "My Feed"
        assert rss.url == "https://mikanani.me/RSS/test"

    async def test_add_without_name_fetches_title(self, rss_engine):
        """add_rss without name calls get_rss_title to auto-discover title."""
        with patch("module.rss.engine.RequestContent") as MockReq:
            mock_instance = AsyncMock()
            mock_instance.get_rss_title = AsyncMock(return_value="Fetched Title")
            MockReq.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockReq.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await rss_engine.add_rss(
                rss_link="https://mikanani.me/RSS/auto",
                name=None,
            )

        assert result.status is True
        rss = await rss_engine.db.rss.search_id(1)
        assert rss.name == "Fetched Title"

    async def test_add_without_name_fetch_fails(self, rss_engine):
        """add_rss returns error when title fetch fails."""
        with patch("module.rss.engine.RequestContent") as MockReq:
            mock_instance = AsyncMock()
            mock_instance.get_rss_title = AsyncMock(return_value=None)
            MockReq.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockReq.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await rss_engine.add_rss(
                rss_link="https://mikanani.me/RSS/broken",
                name=None,
            )

        assert result.status is False
        assert result.status_code == 406

    async def test_add_duplicate_url_fails(self, rss_engine):
        """add_rss with an already-existing URL returns failure."""
        await rss_engine.add_rss(
            rss_link="https://mikanani.me/RSS/dup",
            name="First",
        )
        result = await rss_engine.add_rss(
            rss_link="https://mikanani.me/RSS/dup",
            name="Second",
        )

        assert result.status is False
        assert result.status_code == 406


class TestRefreshRssConcurrency:
    async def test_concurrent_requests_limited(self, rss_engine):
        """refresh_rss should limit concurrent requests via semaphore."""
        rss_items = [
            make_rss_item(name=f"Feed {i}", url=f"https://feed{i}.com/rss")
            for i in range(10)
        ]
        for item in rss_items:
            await rss_engine.db.rss.add(item)

        active_count = 0
        max_active = 0
        lock = asyncio.Lock()

        async def track_concurrency(rss_item):
            nonlocal active_count, max_active
            async with lock:
                active_count += 1
                max_active = max(max_active, active_count)
            await asyncio.sleep(0.01)
            async with lock:
                active_count -= 1
            return [], None

        with patch.object(
            rss_engine, "_pull_rss_with_status", side_effect=track_concurrency
        ):
            client = AsyncMock()
            await rss_engine.refresh_rss(client)

        assert max_active <= 5


# ---------------------------------------------------------------------------
# refresh_rss per-host throttling (#1026)
# ---------------------------------------------------------------------------


class TestRefreshRssPerHostThrottle:
    async def test_same_host_requests_never_overlap(self, rss_engine):
        """Feeds on the same host are fetched serially; other hosts stay parallel."""
        for i in range(3):
            await rss_engine.db.rss.add(
                make_rss_item(url=f"https://nyaa.example/rss/{i}", name=f"nyaa{i}")
            )
        await rss_engine.db.rss.add(
            make_rss_item(url="https://mikan.example/rss", name="mikan")
        )

        from urllib.parse import urlparse

        active: dict[str, int] = {}
        max_active: dict[str, int] = {}

        async def fake_pull(item):
            host = urlparse(item.url).netloc
            active[host] = active.get(host, 0) + 1
            max_active[host] = max(max_active.get(host, 0), active[host])
            # Give concurrently-scheduled pulls a chance to overlap.
            await asyncio.sleep(0.01)
            active[host] -= 1
            return [], None

        client = AsyncMock()
        with (
            patch.object(
                RSSEngine,
                "_pull_rss_with_status",
                new_callable=lambda: AsyncMock(side_effect=fake_pull),
            ),
            patch("module.rss.engine.RSS_PER_HOST_DELAY", 0),
        ):
            await rss_engine.refresh_rss(client)

        assert max_active["nyaa.example"] == 1
        assert max_active["mikan.example"] == 1

    async def test_all_feeds_still_processed(self, rss_engine):
        """Grouping by host must not drop any feed's status update."""
        await rss_engine.db.rss.add(
            make_rss_item(url="https://a.example/rss", name="a")
        )
        await rss_engine.db.rss.add(
            make_rss_item(url="https://b.example/rss", name="b")
        )

        client = AsyncMock()
        with (
            patch.object(
                RSSEngine,
                "_pull_rss_with_status",
                new_callable=lambda: AsyncMock(return_value=([], None)),
            ),
            patch("module.rss.engine.RSS_PER_HOST_DELAY", 0),
        ):
            await rss_engine.refresh_rss(client)

        for rss_id in (1, 2):
            item = await rss_engine.db.rss.search_id(rss_id)
            assert item.connection_status == "healthy"


# ---------------------------------------------------------------------------
# Release-group / resolution preference dedup
# ---------------------------------------------------------------------------


class TestPreferenceDedup:
    """Unit tests for RSSEngine._select_preference_skips."""

    async def test_no_preference_keeps_all_candidates(self, rss_engine):
        """No preferred_group/preferred_resolution set -> nothing is skipped."""
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="", id=1)
        torrent_a = make_torrent(name="[GroupA] Mushoku Tensei - 12 [1080p].mkv")
        torrent_b = make_torrent(name="[GroupB] Mushoku Tensei - 12 [720p].mkv")

        skips = RSSEngine._select_preference_skips(
            [(torrent_a, bangumi), (torrent_b, bangumi)],
            preference_bangumi={},
            existing_downloaded={},
        )

        assert skips == set()

    async def test_batch_picks_preferred_group_skips_other(self, rss_engine):
        """Two releases of the same episode arrive together -> only the
        preferred group is kept."""
        bangumi = make_bangumi(
            title_raw="Mushoku Tensei", filter="", id=1, preferred_group="GroupA"
        )
        preferred = make_torrent(name="[GroupA] Mushoku Tensei - 12 [1080p].mkv")
        other = make_torrent(name="[GroupB] Mushoku Tensei - 12 [1080p].mkv")

        skips = RSSEngine._select_preference_skips(
            [(preferred, bangumi), (other, bangumi)],
            preference_bangumi={1: bangumi},
            existing_downloaded={},
        )

        assert id(other) in skips
        assert id(preferred) not in skips

    async def test_batch_picks_preferred_resolution_skips_other(self, rss_engine):
        """Preference on resolution alone also dedups within a batch."""
        bangumi = make_bangumi(
            title_raw="Mushoku Tensei",
            filter="",
            id=1,
            preferred_resolution="1080p",
        )
        preferred = make_torrent(name="[GroupA] Mushoku Tensei - 12 [1080p].mkv")
        other = make_torrent(name="[GroupB] Mushoku Tensei - 12 [720p].mkv")

        skips = RSSEngine._select_preference_skips(
            [(preferred, bangumi), (other, bangumi)],
            preference_bangumi={1: bangumi},
            existing_downloaded={},
        )

        assert id(other) in skips
        assert id(preferred) not in skips

    async def test_new_release_strictly_better_than_downloaded_is_kept(
        self, rss_engine
    ):
        """A better-matching release replaces a worse already-downloaded one."""
        bangumi = make_bangumi(
            title_raw="Mushoku Tensei", filter="", id=1, preferred_group="GroupA"
        )
        already_downloaded = make_torrent(
            name="[GroupB] Mushoku Tensei - 12 [1080p].mkv", downloaded=True
        )
        better_candidate = make_torrent(name="[GroupA] Mushoku Tensei - 12 [1080p].mkv")

        skips = RSSEngine._select_preference_skips(
            [(better_candidate, bangumi)],
            preference_bangumi={1: bangumi},
            existing_downloaded={1: [already_downloaded]},
        )

        assert skips == set()

    async def test_new_release_not_better_than_downloaded_is_skipped(self, rss_engine):
        """A same-or-worse-matching release does not replace what is already
        downloaded (old download is left in place, new one is just skipped)."""
        bangumi = make_bangumi(
            title_raw="Mushoku Tensei", filter="", id=1, preferred_group="GroupA"
        )
        already_downloaded = make_torrent(
            name="[GroupA] Mushoku Tensei - 12 [1080p].mkv", downloaded=True
        )
        worse_candidate = make_torrent(name="[GroupB] Mushoku Tensei - 12 [720p].mkv")

        skips = RSSEngine._select_preference_skips(
            [(worse_candidate, bangumi)],
            preference_bangumi={1: bangumi},
            existing_downloaded={1: [already_downloaded]},
        )

        assert id(worse_candidate) in skips

    async def test_unparseable_episode_is_never_skipped(self, rss_engine):
        """A candidate whose episode number can't be parsed is a conservative
        fallback: always keep it rather than risk dropping a real episode."""
        bangumi = make_bangumi(
            title_raw="Mushoku Tensei", filter="", id=1, preferred_group="GroupA"
        )
        unparseable = make_torrent(name="Completely Unparseable Blob")

        skips = RSSEngine._select_preference_skips(
            [(unparseable, bangumi)],
            preference_bangumi={1: bangumi},
            existing_downloaded={},
        )

        assert skips == set()

    async def test_different_episodes_are_not_deduped_against_each_other(
        self, rss_engine
    ):
        """Preference dedup only compares candidates for the same episode."""
        bangumi = make_bangumi(
            title_raw="Mushoku Tensei", filter="", id=1, preferred_group="GroupA"
        )
        ep12 = make_torrent(name="[GroupB] Mushoku Tensei - 12 [1080p].mkv")
        ep13 = make_torrent(name="[GroupB] Mushoku Tensei - 13 [1080p].mkv")

        skips = RSSEngine._select_preference_skips(
            [(ep12, bangumi), (ep13, bangumi)],
            preference_bangumi={1: bangumi},
            existing_downloaded={},
        )

        assert skips == set()


class TestRefreshRssPreferenceDedup:
    """Integration coverage through refresh_rss end to end."""

    async def test_refresh_rss_downloads_only_preferred_group(self, rss_engine):
        """Two subtitle groups match the same episode; only the preferred one
        is added to the download client."""
        rss_item = make_rss_item(enabled=True)
        await rss_engine.db.rss.add(rss_item)
        bangumi = make_bangumi(
            title_raw="Mushoku Tensei", filter="", preferred_group="GroupA"
        )
        await rss_engine.db.bangumi.add(bangumi)

        preferred = Torrent(
            name="[GroupA] Mushoku Tensei - 12 [1080p].mkv",
            url="https://example.com/groupa12.torrent",
        )
        other = Torrent(
            name="[GroupB] Mushoku Tensei - 12 [1080p].mkv",
            url="https://example.com/groupb12.torrent",
        )
        with patch.object(
            RSSEngine, "_get_torrents", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [preferred, other]
            client = AsyncMock()
            client.add_torrent = AsyncMock(return_value=AddResult.ADDED)

            await rss_engine.refresh_rss(client)

        client.add_torrent.assert_called_once()
        called_torrent = client.add_torrent.call_args[0][0]
        assert called_torrent.name == preferred.name

        all_torrents = await rss_engine.db.torrent.search_all()
        assert len(all_torrents) == 2
        downloaded = {t.name: t.downloaded for t in all_torrents}
        assert downloaded[preferred.name] is True
        assert downloaded[other.name] is False

    async def test_refresh_rss_no_preference_downloads_both_groups(self, rss_engine):
        """Regression: with no preference set, both groups still download
        (unchanged legacy behavior)."""
        rss_item = make_rss_item(enabled=True)
        await rss_engine.db.rss.add(rss_item)
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="")
        await rss_engine.db.bangumi.add(bangumi)

        torrent_a = Torrent(
            name="[GroupA] Mushoku Tensei - 12 [1080p].mkv",
            url="https://example.com/groupa12.torrent",
        )
        torrent_b = Torrent(
            name="[GroupB] Mushoku Tensei - 12 [1080p].mkv",
            url="https://example.com/groupb12.torrent",
        )
        with patch.object(
            RSSEngine, "_get_torrents", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = [torrent_a, torrent_b]
            client = AsyncMock()
            client.add_torrent = AsyncMock(return_value=AddResult.ADDED)

            await rss_engine.refresh_rss(client)

        assert client.add_torrent.call_count == 2
