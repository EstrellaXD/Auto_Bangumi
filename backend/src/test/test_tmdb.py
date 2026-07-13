"""Tests for the TMDB parser.

The default (mocked) test never touches the network: it patches
``RequestContent.get_json`` with fixture data so the suite stays
deterministic and offline. A separate live test exercises the real TMDB API
and is skipped unless explicitly opted into.
"""

import importlib
import os
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest

from module.parser.analyser.tmdb_parser import tmdb_parser

# `module.parser.analyser.__init__` re-exports the `tmdb_parser` function under
# the same name as this submodule, shadowing the submodule on the package
# object — so `import module.parser.analyser.tmdb_parser as x` would resolve
# to the function, not the module. Go through importlib to get the module.
tmdb_parser_module = importlib.import_module("module.parser.analyser.tmdb_parser")


def _query_params(url: str) -> dict[str, list[str]]:
    return parse_qs(urlsplit(url).query)


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

    search_requests: list[tuple[str, dict[str, list[str]]]] = []

    async def fake_get_json(url: str) -> dict:
        if "/search/tv" in url:
            search_requests.append(("tv", _query_params(url)))
            return {"results": []}
        if "/search/movie" in url:
            search_requests.append(("movie", _query_params(url)))
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
    assert [
        (kind, query["query"], query["language"]) for kind, query in search_requests
    ] == [
        ("tv", ["你的名字"], ["zh-CN"]),
        ("tv", ["你的名字"], ["zh-CN"]),
        ("movie", ["你的名字"], ["zh-CN"]),
    ]


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


async def test_tv_whitespace_retry_preserves_language(mocker):
    search_requests: list[dict[str, list[str]]] = []

    async def fake_get_json(url: str) -> dict:
        if "/search/tv" in url:
            query = _query_params(url)
            search_requests.append(query)
            if query["query"] == ["海 盗 战 记"]:
                return {"results": []}
            return {"results": [{"id": 82684}]}
        if "/season/" in url:
            return {"episodes": []}
        return _SHOW_INFO

    mocker.patch.object(
        tmdb_parser_module.RequestContent, "get_json", side_effect=fake_get_json
    )
    tmdb_parser_module._tmdb_cache.clear()

    tmdb_info = await tmdb_parser("海 盗 战 记", "jp", test=True)

    assert tmdb_info is not None
    assert [query["query"] for query in search_requests] == [
        ["海 盗 战 记"],
        ["海盗战记"],
    ]
    assert [query["language"] for query in search_requests] == [
        ["ja-JP"],
        ["ja-JP"],
    ]


async def test_movie_whitespace_retry_preserves_language(mocker):
    search_requests: list[dict[str, list[str]]] = []

    async def fake_get_json(url: str) -> dict:
        if "/search/movie" not in url:
            return {}
        query = _query_params(url)
        search_requests.append(query)
        if query["query"] == ["Your Name"]:
            return {"results": []}
        return _MOVIE_SEARCH_RESULT

    mocker.patch.object(
        tmdb_parser_module.RequestContent, "get_json", side_effect=fake_get_json
    )
    tmdb_parser_module._tmdb_cache.clear()

    tmdb_info = await tmdb_parser("Your Name", "en", test=True, is_movie=True)

    assert tmdb_info is not None
    assert [query["query"] for query in search_requests] == [
        ["Your Name"],
        ["YourName"],
    ]
    assert [query["language"] for query in search_requests] == [
        ["en-US"],
        ["en-US"],
    ]


async def test_tmdb_parser_movie_search_no_results_returns_none(mocker):
    async def fake_get_json(url: str) -> dict:
        return {"results": []}

    mocker.patch.object(
        tmdb_parser_module.RequestContent, "get_json", side_effect=fake_get_json
    )
    tmdb_parser_module._tmdb_cache.clear()

    tmdb_info = await tmdb_parser("不存在的电影", "zh", test=True, is_movie=True)

    assert tmdb_info is None


@pytest.mark.parametrize(
    ("builder_name", "path"),
    (("search_url", "/3/search/tv"), ("search_movie_url", "/3/search/movie")),
)
@pytest.mark.parametrize(
    ("language", "expected_locale"),
    (("zh", "zh-CN"), ("jp", "ja-JP"), ("en", "en-US")),
)
def test_search_urls_encode_query_and_language(
    builder_name: str,
    path: str,
    language: str,
    expected_locale: str,
):
    title = "关于我转生变成史莱姆 & Friends"
    with patch.object(tmdb_parser_module, "settings") as mock_settings:
        mock_settings.network.tmdb_base_url = "https://tmdb.example/base/"
        mock_settings.network.tmdb_api_key = "custom key"
        builder = getattr(tmdb_parser_module, builder_name)
        url = builder(title, language)

    parsed = urlsplit(url)
    assert parsed.scheme == "https"
    assert parsed.netloc == "tmdb.example"
    assert parsed.path == f"/base{path}"
    assert parse_qs(parsed.query) == {
        "api_key": ["custom key"],
        "page": ["1"],
        "query": [title],
        "include_adult": ["false"],
        "language": [expected_locale],
    }


def test_search_url_uses_custom_api_key():
    """用户自配的 TMDB API key 优先于内置共享 key (#975)。"""
    with patch.object(tmdb_parser_module, "settings") as mock_settings:
        mock_settings.network.tmdb_base_url = "https://api.themoviedb.org"
        mock_settings.network.tmdb_api_key = "customkey123"
        url = tmdb_parser_module.search_url("test", "zh")

    assert _query_params(url)["api_key"] == ["customkey123"]


def test_search_url_falls_back_to_builtin_key():
    from module.conf import TMDB_API

    with patch.object(tmdb_parser_module, "settings") as mock_settings:
        mock_settings.network.tmdb_base_url = "https://api.themoviedb.org"
        mock_settings.network.tmdb_api_key = ""
        url = tmdb_parser_module.search_url("test", "zh")

    assert _query_params(url)["api_key"] == [TMDB_API]


def test_network_config_tmdb_api_key_defaults_empty():
    from module.models.config import Network

    assert Network().tmdb_api_key == ""


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
