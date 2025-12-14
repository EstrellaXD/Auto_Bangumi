"""
Tests for MikanWebParser.
Based on Goto_Bangumi/internal/parser/mikan_test.go
"""

import time
from pathlib import Path

import pytest

from module.network.request_contents import _cache
from module.parser.analyser.mikan_parser import MikanWebParser, chinese_to_num
from module.utils import gen_poster_path


TESTDATA_DIR = Path(__file__).parent / "testdata"


def load_html(filename: str) -> str:
    return (TESTDATA_DIR / filename).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def setup_cache():
    """Setup cache with test HTML before each test."""
    test_cases = [
        ("https://mikanani.me/Home/Episode/8c94c1699735481c8b2b18dba38908042f53adcc", "mikan_3751.html"),
        ("https://mikanani.me/Home/Episode/f2340bae48a4c7eae1421190d603d4c889d490b7", "mikan_3790.html"),
        ("https://mikanani.me/Home/Episode/8c2e3e9f7b71419a513d2647f5004f3a0f08a7f0", "mikan_3599.html"),
        ("https://mikanani.me/Home/Episode/699000310671bae565c37abb20d119824efeb6f0", "mikan_edge_case.html"),
    ]
    for url, html_file in test_cases:
        _cache[url] = {"data": load_html(html_file), "timestamp": time.time()}
    yield
    _cache.clear()


def poster(url: str) -> str:
    return gen_poster_path(url)


class TestMikanWebParser:
    @pytest.fixture
    def parser(self):
        return MikanWebParser()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "homepage,want_id,want_title,want_season,want_poster",
        [
            (
                "https://mikanani.me/Home/Episode/8c94c1699735481c8b2b18dba38908042f53adcc",
                "3751#1230",
                "拥有超常技能的异世界流浪美食家",
                2,
                "https://mikanani.me/images/Bangumi/202510/0710007f.jpg",
            ),
            (
                "https://mikanani.me/Home/Episode/f2340bae48a4c7eae1421190d603d4c889d490b7",
                "3790#370",
                "妖怪旅馆营业中",
                2,
                "https://mikanani.me/images/Bangumi/202510/0d10efc3.jpg",
            ),
            (
                "https://mikanani.me/Home/Episode/8c2e3e9f7b71419a513d2647f5004f3a0f08a7f0",
                "3599#1208",
                "夏日口袋",
                1,
                "https://mikanani.me/images/Bangumi/202504/076c1094.jpg",
            ),
        ],
    )
    async def test_parser(self, parser, homepage, want_id, want_title, want_season, want_poster):
        info = await parser.parser(homepage)

        assert info is not None
        assert info.id == want_id
        assert info.official_title == want_title
        assert info.season == want_season
        assert info.poster_link == poster(want_poster)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "homepage,want_poster",
        [
            (
                "https://mikanani.me/Home/Episode/8c94c1699735481c8b2b18dba38908042f53adcc",
                "https://mikanani.me/images/Bangumi/202510/0710007f.jpg",
            ),
            (
                "https://mikanani.me/Home/Episode/8c2e3e9f7b71419a513d2647f5004f3a0f08a7f0",
                "https://mikanani.me/images/Bangumi/202504/076c1094.jpg",
            ),
        ],
    )
    async def test_poster_parser(self, parser, homepage, want_poster):
        poster_link = await parser.poster_parser(homepage)

        assert poster_link == poster(want_poster)


class TestMikanParserEdgeCase:
    @pytest.fixture
    def parser(self):
        return MikanWebParser()

    @pytest.mark.asyncio
    async def test_no_rss_link(self, parser):
        """Page without RSS link should return empty MikanInfo."""
        homepage = "https://mikanani.me/Home/Episode/699000310671bae565c37abb20d119824efeb6f0"
        info = await parser.parser(homepage)
        # No bangumi-title element, returns empty MikanInfo
        assert info is not None
        assert info.id == ""
        assert info.official_title == ""

    @pytest.mark.asyncio
    async def test_default_poster(self, parser):
        """Page with default image should return empty string."""
        homepage = "https://mikanani.me/Home/Episode/699000310671bae565c37abb20d119824efeb6f0"
        poster_link = await parser.poster_parser(homepage)
        assert poster_link == ""

    @pytest.mark.asyncio
    async def test_non_mikan_page(self, parser):
        """Non-Mikan page should raise MikanPageParseError."""
        homepage = "https://example.com/some/page"
        _cache[homepage] = {"data": "<html><body>Not Mikan</body></html>", "timestamp": time.time()}

        from module.exceptions import MikanPageParseError

        with pytest.raises(MikanPageParseError):
            await parser.parser(homepage)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
