"""Tests for the TMDB parser.

The default (mocked) test never touches the network: it patches
``RequestContent.get_json`` with fixture data so the suite stays
deterministic and offline. A separate live test exercises the real TMDB API
and is skipped unless explicitly opted into.
"""

import importlib
import os

import pytest

from module.parser.analyser.tmdb_parser import tmdb_parser

# `module.parser.analyser.__init__` re-exports the `tmdb_parser` function under
# the same name as this submodule, shadowing the submodule on the package
# object — so `import module.parser.analyser.tmdb_parser as x` would resolve
# to the function, not the module. Go through importlib to get the module.
tmdb_parser_module = importlib.import_module("module.parser.analyser.tmdb_parser")

_SHOW_INFO = {
    "genres": [{"id": 16, "name": "Animation"}],
    "name": "冰海战记",
    "original_name": "ヴィンランド・サガ",
    "first_air_date": "2019-07-08",
    "status": "Ended",
    "poster_path": "/poster.jpg",
    "seasons": [
        {
            "name": "第 1 季",
            "air_date": "2019-07-08",
            "poster_path": "/s1.jpg",
            "season_number": 1,
            "episode_count": 24,
        },
        {
            "name": "第 2 季",
            "air_date": "2023-01-09",
            "poster_path": "/s2.jpg",
            "season_number": 2,
            "episode_count": 24,
        },
    ],
}


async def _fake_get_json(url: str) -> dict:
    if "/search/tv" in url:
        return {"results": [{"id": 82684}]}
    if "/season/" in url:
        return {"episodes": []}
    return _SHOW_INFO


async def test_tmdb_parser(mocker):
    mocker.patch.object(
        tmdb_parser_module.RequestContent, "get_json", side_effect=_fake_get_json
    )
    tmdb_parser_module._tmdb_cache.clear()

    bangumi_title = "海盗战记"
    bangumi_year = "2019"
    bangumi_season = 2

    tmdb_info = await tmdb_parser(bangumi_title, "zh", test=True)

    assert tmdb_info is not None
    assert tmdb_info.title == "冰海战记"
    assert tmdb_info.year == bangumi_year
    assert tmdb_info.last_season == bangumi_season


_MOVIE_SEARCH_RESULT = {
    "results": [
        {
            "id": 372058,
            "title": "你的名字。",
            "original_title": "君の名は。",
            "release_date": "2016-08-26",
            "poster_path": "/movie_poster.jpg",
        }
    ]
}


async def test_tmdb_parser_movie_fallback_when_tv_search_misses(mocker):
    """When search/tv has no results at all, fall back to search/movie
    (e.g. for a theatrical release with no matching TV series)."""

    async def fake_get_json(url: str) -> dict:
        if "/search/tv" in url:
            return {"results": []}
        if "/search/movie" in url:
            return _MOVIE_SEARCH_RESULT
        return {}

    mocker.patch.object(
        tmdb_parser_module.RequestContent, "get_json", side_effect=fake_get_json
    )
    tmdb_parser_module._tmdb_cache.clear()

    tmdb_info = await tmdb_parser("你的名字", "zh", test=True)

    assert tmdb_info is not None
    assert tmdb_info.title == "你的名字。"
    assert tmdb_info.original_title == "君の名は。"
    assert tmdb_info.year == "2016"
    assert tmdb_info.last_season == 0


async def test_tmdb_parser_is_movie_queries_movie_search_directly(mocker):
    """is_movie=True skips the TV search entirely and queries search/movie."""
    tv_search_called = False

    async def fake_get_json(url: str) -> dict:
        nonlocal tv_search_called
        if "/search/tv" in url:
            tv_search_called = True
            return {"results": [{"id": 1}]}
        if "/search/movie" in url:
            return _MOVIE_SEARCH_RESULT
        return {}

    mocker.patch.object(
        tmdb_parser_module.RequestContent, "get_json", side_effect=fake_get_json
    )
    tmdb_parser_module._tmdb_cache.clear()

    tmdb_info = await tmdb_parser("你的名字", "zh", test=True, is_movie=True)

    assert tv_search_called is False
    assert tmdb_info is not None
    assert tmdb_info.title == "你的名字。"


async def test_tmdb_parser_movie_search_no_results_returns_none(mocker):
    async def fake_get_json(url: str) -> dict:
        return {"results": []}

    mocker.patch.object(
        tmdb_parser_module.RequestContent, "get_json", side_effect=fake_get_json
    )
    tmdb_parser_module._tmdb_cache.clear()

    tmdb_info = await tmdb_parser("不存在的电影", "zh", test=True, is_movie=True)

    assert tmdb_info is None


def test_reset_cache_clears_tmdb_cache():
    """reset_cache() must drop all cached lookups (called on config reload so
    a changed tmdb_base_url stops serving results from the old endpoint)."""
    tmdb_parser_module._tmdb_cache["stale-key"] = None
    assert len(tmdb_parser_module._tmdb_cache) > 0

    tmdb_parser_module.reset_cache()

    assert len(tmdb_parser_module._tmdb_cache) == 0


@pytest.mark.live
@pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_TMDB_TESTS"),
    reason="hits the real TMDB API; set RUN_LIVE_TMDB_TESTS=1 to run",
)
async def test_tmdb_parser_live():
    tmdb_parser_module._tmdb_cache.clear()

    bangumi_title = "海盗战记"
    bangumi_year = "2019"
    bangumi_season = 2

    tmdb_info = await tmdb_parser(bangumi_title, "zh", test=True)

    assert tmdb_info is not None
    assert tmdb_info.title == "冰海战记"
    assert tmdb_info.year == bangumi_year
    assert tmdb_info.last_season == bangumi_season
