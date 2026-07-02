"""Tests for search providers: URL construction, keyword handling."""

from unittest.mock import AsyncMock, patch

import pytest

from module.models import Bangumi, RSSItem
from module.searcher.provider import search_url

# ---------------------------------------------------------------------------
# search_url
# ---------------------------------------------------------------------------


class TestSearchUrl:
    @pytest.fixture(autouse=True)
    def mock_search_config(self):
        """Ensure SEARCH_CONFIG has default providers."""
        config = {
            "mikan": "https://mikanani.me/RSS/Search?searchstr=%s",
            "nyaa": "https://nyaa.si/?page=rss&q=%s&c=0_0&f=0",
            "dmhy": "http://dmhy.org/topics/rss/rss.xml?keyword=%s",
        }
        with patch("module.searcher.provider.SEARCH_CONFIG", config):
            yield

    def test_mikan_url(self):
        """Mikan search URL is constructed correctly."""
        result = search_url("mikan", ["Mushoku", "Tensei"])
        assert isinstance(result, RSSItem)
        assert "mikanani.me" in result.url
        assert "Mushoku" in result.url
        assert "Tensei" in result.url
        assert result.parser == "mikan"

    def test_nyaa_url(self):
        """Nyaa search URL is constructed correctly."""
        result = search_url("nyaa", ["Mushoku", "Tensei"])
        assert "nyaa.si" in result.url
        assert result.parser == "tmdb"

    def test_dmhy_url(self):
        """DMHY search URL is constructed correctly."""
        result = search_url("dmhy", ["Mushoku", "Tensei"])
        assert "dmhy.org" in result.url
        assert result.parser == "tmdb"

    def test_unsupported_site_raises(self):
        """Unknown site raises ValueError."""
        with pytest.raises(ValueError, match="not supported"):
            search_url("unknown_site", ["test"])

    def test_keyword_sanitization(self):
        """Non-word characters are replaced with +."""
        result = search_url("mikan", ["Test Anime (2024)"])
        # Spaces and parentheses should be replaced with +
        assert "(" not in result.url
        assert ")" not in result.url

    def test_multiple_keywords_joined(self):
        """Multiple keywords are joined with +."""
        result = search_url("mikan", ["word1", "word2", "word3"])
        # All keywords should appear in the URL
        url = result.url
        assert "word1" in url
        assert "word2" in url
        assert "word3" in url

    def test_aggregate_is_false(self):
        """Search RSS items have aggregate=False."""
        result = search_url("mikan", ["test"])
        assert result.aggregate is False


# ---------------------------------------------------------------------------
# SearchTorrent.special_url
# ---------------------------------------------------------------------------


class TestSpecialUrl:
    def test_uses_bangumi_fields(self):
        """special_url builds keywords from SEARCH_KEY fields of Bangumi."""
        from module.searcher.searcher import SEARCH_KEY, SearchTorrent
        from test.factories import make_bangumi

        bangumi = make_bangumi(
            group_name="SubGroup",
            title_raw="Test Raw",
            season_raw="S2",
            dpi="1080p",
            source="Web",
            subtitle="CHT",
        )

        with patch(
            "module.searcher.provider.SEARCH_CONFIG",
            {
                "mikan": "https://mikanani.me/RSS/Search?searchstr=%s",
            },
        ):
            result = SearchTorrent.special_url(bangumi, "mikan")

        assert isinstance(result, RSSItem)
        # All non-None SEARCH_KEY fields should contribute to the URL
        assert "SubGroup" in result.url
        assert "Test" in result.url

    def test_skips_none_fields(self):
        """special_url skips fields that are None."""
        from module.searcher.searcher import SearchTorrent
        from test.factories import make_bangumi

        bangumi = make_bangumi(
            group_name=None,
            title_raw="Test",
            season_raw=None,
            dpi=None,
            source=None,
            subtitle=None,
        )

        with patch(
            "module.searcher.provider.SEARCH_CONFIG",
            {
                "mikan": "https://mikanani.me/RSS/Search?searchstr=%s",
            },
        ):
            result = SearchTorrent.special_url(bangumi, "mikan")

        # Only title_raw should be in the URL
        assert "Test" in result.url


# ---------------------------------------------------------------------------
# _poster_cache: bounded LRU + reset_cache()
# ---------------------------------------------------------------------------


class TestPosterCache:
    @pytest.fixture(autouse=True)
    def _clean_poster_cache(self):
        """Isolate the module-level poster cache between tests."""
        from module.searcher import searcher as searcher_module

        searcher_module.reset_cache()
        yield
        searcher_module.reset_cache()

    def test_reset_cache_clears_poster_cache(self):
        from module.searcher import searcher as searcher_module

        searcher_module._poster_cache["Test Anime"] = "http://example.com/p.jpg"
        assert len(searcher_module._poster_cache) > 0

        searcher_module.reset_cache()

        assert len(searcher_module._poster_cache) == 0

    async def test_poster_cache_evicts_oldest_when_full(self, monkeypatch):
        """_poster_cache is bounded (LRU-ish) like _tmdb_cache/_mikan_cache,
        instead of growing without limit for the life of the process."""
        from module.searcher import searcher as searcher_module
        from module.searcher.searcher import SearchTorrent

        monkeypatch.setattr(searcher_module, "_POSTER_CACHE_MAX", 3)
        torrent = SearchTorrent()

        with patch(
            "module.searcher.searcher.tmdb_parser", new=AsyncMock(return_value=None)
        ):
            for i in range(4):
                await torrent._fetch_tmdb_poster(f"Title {i}")

        assert len(searcher_module._poster_cache) == 3
        # The oldest entry ("Title 0") was evicted; the rest remain.
        assert "Title 0" not in searcher_module._poster_cache
        assert "Title 3" in searcher_module._poster_cache
