"""
Tests for TMDB parser.
Based on Goto_Bangumi/internal/parser/tmdb_test.go
"""

import json
import time
from pathlib import Path

import pytest

from module.network.request_contents import _cache
from module.parser.tmdb import tmdb_parser
from module.parser.parser_config import search_url, info_url, TMDB_IMG_URL
from module.utils import gen_poster_path


TESTDATA_DIR = Path(__file__).parent / "testdata"


def load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def setup_cache():
    """Setup cache with test JSON before each test."""
    search_data = load_json("tmdb_search_wolf.json")
    info_data = load_json("tmdb_info_229676.json")

    # Cache search URL for "狼与香辛料"
    _cache[search_url("狼与香辛料")] = {"data": search_data, "timestamp": time.time()}

    # Cache info URL for show 229676
    _cache[info_url("229676", "zh")] = {"data": info_data, "timestamp": time.time()}

    yield
    _cache.clear()


def poster(path: str) -> str:
    return gen_poster_path(f"{TMDB_IMG_URL}{path}")


class TestTMDBParser:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "title,want_id,want_title,want_original_title,want_year,want_season,want_poster_path",
        [
            (
                "狼与香辛料",
                229676,
                "狼与香辛料 行商邂逅贤狼",
                "狼と香辛料 MERCHANT MEETS THE WISE WOLF",
                "2024",
                1,
                "/vgfhyqA6n8WWiDhHXdVRBMHAqQw.jpg",
            ),
        ],
    )
    async def test_tmdb_parse(
        self,
        title,
        want_id,
        want_title,
        want_original_title,
        want_year,
        want_season,
        want_poster_path,
    ):
        info = await tmdb_parser(title, "zh")

        assert info is not None, f"tmdb_parser() returned None for title: {title}"
        assert info.id == want_id, f"tmdb_parser() id = {info.id}, want {want_id}"
        assert info.title == want_title, f"tmdb_parser() title = {info.title}, want {want_title}"
        assert (
            info.original_title == want_original_title
        ), f"tmdb_parser() original_title = {info.original_title}, want {want_original_title}"
        assert info.year == want_year, f"tmdb_parser() year = {info.year}, want {want_year}"
        assert info.season == want_season, f"tmdb_parser() season = {info.season}, want {want_season}"
        assert info.poster_link == poster(want_poster_path), f"tmdb_parser() poster_link = {info.poster_link}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
