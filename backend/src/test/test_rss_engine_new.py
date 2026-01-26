"""Tests for RSS engine: pull_rss, match_torrent, refresh_rss, add_rss."""

import pytest
from unittest.mock import AsyncMock, patch

from sqlmodel import Session

from module.database.bangumi import BangumiDatabase, _invalidate_bangumi_cache
from module.database.rss import RSSDatabase
from module.database.torrent import TorrentDatabase
from module.models import Bangumi, RSSItem, Torrent
from module.rss.engine import RSSEngine

from test.factories import make_bangumi, make_torrent, make_rss_item


@pytest.fixture
def rss_engine(db_engine):
    """RSSEngine backed by in-memory database."""
    engine = RSSEngine(_engine=db_engine)
    return engine


@pytest.fixture(autouse=True)
def clear_bangumi_cache():
    """Invalidate bangumi cache before each test."""
    _invalidate_bangumi_cache()
    yield
    _invalidate_bangumi_cache()


# ---------------------------------------------------------------------------
# pull_rss
# ---------------------------------------------------------------------------


class TestPullRss:
    async def test_returns_only_new_torrents(self, rss_engine):
        """pull_rss filters out torrents already in the database."""
        rss_item = make_rss_item()
        rss_engine.rss.add(rss_item)
        rss_item = rss_engine.rss.search_id(1)

        # Pre-insert one torrent into DB
        existing = make_torrent(url="https://example.com/existing.torrent", rss_id=1)
        rss_engine.torrent.add(existing)

        # Mock _get_torrents to return 3 torrents (1 existing + 2 new)
        all_torrents = [
            Torrent(name="existing", url="https://example.com/existing.torrent"),
            Torrent(name="new1", url="https://example.com/new1.torrent"),
            Torrent(name="new2", url="https://example.com/new2.torrent"),
        ]
        with patch.object(RSSEngine, "_get_torrents", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = all_torrents
            result = await rss_engine.pull_rss(rss_item)

        assert len(result) == 2
        assert all(t.url != "https://example.com/existing.torrent" for t in result)

    async def test_all_existing_returns_empty(self, rss_engine):
        """When all torrents already exist, returns empty list."""
        rss_item = make_rss_item()
        rss_engine.rss.add(rss_item)
        rss_item = rss_engine.rss.search_id(1)

        existing = make_torrent(url="https://example.com/only.torrent", rss_id=1)
        rss_engine.torrent.add(existing)

        with patch.object(RSSEngine, "_get_torrents", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                Torrent(name="only", url="https://example.com/only.torrent")
            ]
            result = await rss_engine.pull_rss(rss_item)

        assert result == []

    async def test_empty_feed_returns_empty(self, rss_engine):
        """When RSS feed has no torrents, returns empty list."""
        rss_item = make_rss_item()
        rss_engine.rss.add(rss_item)
        rss_item = rss_engine.rss.search_id(1)

        with patch.object(RSSEngine, "_get_torrents", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            result = await rss_engine.pull_rss(rss_item)

        assert result == []


# ---------------------------------------------------------------------------
# match_torrent
# ---------------------------------------------------------------------------


class TestMatchTorrent:
    def test_matches_by_title_raw_substring(self, rss_engine):
        """match_torrent finds Bangumi when title_raw is a substring of torrent name."""
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="")
        rss_engine.bangumi.add(bangumi)

        torrent = make_torrent(
            name="[Lilith-Raws] Mushoku Tensei - 11 [1080p].mkv"
        )
        result = rss_engine.match_torrent(torrent)

        assert result is not None
        assert result.title_raw == "Mushoku Tensei"

    def test_no_match_returns_none(self, rss_engine):
        """Returns None when no Bangumi matches the torrent name."""
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="")
        rss_engine.bangumi.add(bangumi)

        torrent = make_torrent(name="[Sub] Completely Different Anime - 01.mkv")
        result = rss_engine.match_torrent(torrent)

        assert result is None

    def test_filter_excludes_matching_torrent(self, rss_engine):
        """When torrent name matches the filter regex, returns None."""
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="720")
        rss_engine.bangumi.add(bangumi)

        torrent = make_torrent(
            name="[Sub] Mushoku Tensei - 01 [720p].mkv"
        )
        result = rss_engine.match_torrent(torrent)

        assert result is None

    def test_empty_filter_allows_match(self, rss_engine):
        """When filter is empty string, all matching torrents pass."""
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="")
        rss_engine.bangumi.add(bangumi)

        torrent = make_torrent(
            name="[Sub] Mushoku Tensei - 01 [720p].mkv"
        )
        result = rss_engine.match_torrent(torrent)

        assert result is not None

    def test_filter_case_insensitive(self, rss_engine):
        """Filter regex matching is case-insensitive."""
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="HEVC")
        rss_engine.bangumi.add(bangumi)

        # Torrent has "hevc" in lowercase - should still be filtered
        torrent = make_torrent(
            name="[Sub] Mushoku Tensei - 01 [1080p][hevc].mkv"
        )
        result = rss_engine.match_torrent(torrent)

        assert result is None

    def test_deleted_bangumi_not_matched(self, rss_engine):
        """Bangumi with deleted=True should not match."""
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="", deleted=True)
        rss_engine.bangumi.add(bangumi)

        torrent = make_torrent(name="[Sub] Mushoku Tensei - 01 [1080p].mkv")
        result = rss_engine.match_torrent(torrent)

        assert result is None

    def test_comma_separated_filters(self, rss_engine):
        """Multiple comma-separated filters are joined with | for OR matching."""
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="720,480")
        rss_engine.bangumi.add(bangumi)

        # Matches one of the filters
        torrent = make_torrent(name="[Sub] Mushoku Tensei - 01 [480p].mkv")
        result = rss_engine.match_torrent(torrent)

        assert result is None

        # Doesn't match any filter
        torrent2 = make_torrent(name="[Sub] Mushoku Tensei - 01 [1080p].mkv")
        result2 = rss_engine.match_torrent(torrent2)

        assert result2 is not None


# ---------------------------------------------------------------------------
# refresh_rss
# ---------------------------------------------------------------------------


class TestRefreshRss:
    async def test_downloads_matched_torrents(self, rss_engine, mock_qb_client):
        """refresh_rss downloads torrents that match a bangumi rule."""
        # Setup DB
        rss_item = make_rss_item(enabled=True)
        rss_engine.rss.add(rss_item)
        bangumi = make_bangumi(title_raw="Mushoku Tensei", filter="")
        rss_engine.bangumi.add(bangumi)

        # Mock network
        new_torrent = Torrent(
            name="[Sub] Mushoku Tensei - 12 [1080p].mkv",
            url="https://example.com/ep12.torrent",
        )
        with patch.object(RSSEngine, "_get_torrents", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [new_torrent]

            # Create a mock client
            client = AsyncMock()
            client.add_torrent = AsyncMock(return_value=True)

            await rss_engine.refresh_rss(client)

        # Verify download was attempted
        client.add_torrent.assert_called_once()
        # Verify torrent stored in DB
        all_torrents = rss_engine.torrent.search_all()
        assert len(all_torrents) == 1
        assert all_torrents[0].downloaded is True

    async def test_unmatched_torrents_stored_not_downloaded(self, rss_engine):
        """Unmatched torrents are stored in DB but not marked downloaded."""
        rss_item = make_rss_item(enabled=True)
        rss_engine.rss.add(rss_item)
        # No bangumi in DB to match

        unmatched = Torrent(
            name="[Sub] Unknown Anime - 01 [1080p].mkv",
            url="https://example.com/unknown.torrent",
        )
        with patch.object(RSSEngine, "_get_torrents", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [unmatched]
            client = AsyncMock()
            await rss_engine.refresh_rss(client)

        client.add_torrent.assert_not_called()
        all_torrents = rss_engine.torrent.search_all()
        assert len(all_torrents) == 1
        assert all_torrents[0].downloaded is False

    async def test_refresh_specific_rss_id(self, rss_engine):
        """refresh_rss with rss_id only processes that specific feed."""
        rss1 = make_rss_item(name="Feed 1", url="https://feed1.com/rss")
        rss2 = make_rss_item(name="Feed 2", url="https://feed2.com/rss")
        rss_engine.rss.add(rss1)
        rss_engine.rss.add(rss2)

        with patch.object(RSSEngine, "_get_torrents", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            client = AsyncMock()
            await rss_engine.refresh_rss(client, rss_id=2)

        # Only called once (for rss_id=2)
        mock_get.assert_called_once()

    async def test_refresh_nonexistent_rss_id(self, rss_engine):
        """refresh_rss with non-existent rss_id does nothing."""
        with patch.object(RSSEngine, "_get_torrents", new_callable=AsyncMock) as mock_get:
            client = AsyncMock()
            await rss_engine.refresh_rss(client, rss_id=999)

        mock_get.assert_not_called()


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
        rss = rss_engine.rss.search_id(1)
        assert rss.name == "My Feed"
        assert rss.url == "https://mikanani.me/RSS/test"

    async def test_add_without_name_fetches_title(self, rss_engine):
        """add_rss without name calls get_rss_title to auto-discover title."""
        with patch(
            "module.rss.engine.RequestContent"
        ) as MockReq:
            mock_instance = AsyncMock()
            mock_instance.get_rss_title = AsyncMock(return_value="Fetched Title")
            MockReq.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockReq.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await rss_engine.add_rss(
                rss_link="https://mikanani.me/RSS/auto",
                name=None,
            )

        assert result.status is True
        rss = rss_engine.rss.search_id(1)
        assert rss.name == "Fetched Title"

    async def test_add_without_name_fetch_fails(self, rss_engine):
        """add_rss returns error when title fetch fails."""
        with patch(
            "module.rss.engine.RequestContent"
        ) as MockReq:
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
