"""Tests for search providers: URL construction, keyword handling."""

import pytest
from unittest.mock import patch

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
        from module.searcher.searcher import SearchTorrent, SEARCH_KEY
        from test.factories import make_bangumi

        bangumi = make_bangumi(
            group_name="SubGroup",
            title_raw="Test Raw",
            season_raw="S2",
            dpi="1080p",
            source="Web",
            subtitle="CHT",
        )

        with patch("module.searcher.provider.SEARCH_CONFIG", {
            "mikan": "https://mikanani.me/RSS/Search?searchstr=%s",
        }):
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

        with patch("module.searcher.provider.SEARCH_CONFIG", {
            "mikan": "https://mikanani.me/RSS/Search?searchstr=%s",
        }):
            result = SearchTorrent.special_url(bangumi, "mikan")

        # Only title_raw should be in the URL
        assert "Test" in result.url
