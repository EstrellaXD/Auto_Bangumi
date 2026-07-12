"""Runtime TMDB localization, URL encoding, movie, and retry coverage."""

from typing import Any

import pytest

pytestmark = pytest.mark.e2e


def _activate(mock_upstream, scenario: str) -> None:
    response = mock_upstream.client.put(f"/__admin/scenario/{scenario}")
    assert response.status_code == 200
    assert response.json() == {"scenario": scenario}


def _configure_tmdb(backend, mock_upstream, language: str) -> None:
    def mutate(config: dict[str, Any]) -> None:
        config["network"]["tmdb_base_url"] = f"{mock_upstream.base_url}/tmdb"
        config["network"]["bgm_base_url"] = f"{mock_upstream.base_url}/bgm"
        config["rss_parser"]["language"] = language
        config["update"]["auto_check"] = False

    backend.update_config(mutate)


def _analyse(backend, mock_upstream, fixture: str) -> dict[str, Any]:
    response = backend.client.post(
        "/api/v1/rss/analysis",
        json={
            "name": fixture,
            "url": f"{mock_upstream.base_url}/rss/{fixture}",
            "aggregate": False,
            "parser": "tmdb",
            "enabled": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _tmdb_requests(mock_upstream) -> list[dict[str, Any]]:
    response = mock_upstream.client.get("/__admin/requests")
    assert response.status_code == 200
    return [
        request
        for request in response.json()["requests"]
        if request["path"].startswith("/tmdb/")
    ]


def test_language_change_requeries_the_same_title_with_localized_urls(
    backend_factory,
    mock_upstream,
):
    backend = backend_factory()
    backend.setup_and_login()
    assert mock_upstream.client.post("/__admin/reset").status_code == 200

    _activate(mock_upstream, "localized-tv-zh")
    _configure_tmdb(backend, mock_upstream, "zh")
    chinese = _analyse(backend, mock_upstream, "tmdb-tv.xml")
    assert chinese["official_title"] == "本地化动画"

    _activate(mock_upstream, "localized-tv-jp")
    _configure_tmdb(backend, mock_upstream, "jp")
    japanese = _analyse(backend, mock_upstream, "tmdb-tv.xml")
    assert japanese["official_title"] == "ローカライズアニメ"

    searches = [
        request
        for request in _tmdb_requests(mock_upstream)
        if request["path"] == "/tmdb/3/search/tv"
    ]
    observed = [
        (request["query"]["query"], request["query"]["language"])
        for request in searches
        if request["query"]["query"] == ["Localized Show"]
    ]
    assert (["Localized Show"], ["zh-CN"]) in observed
    assert (["Localized Show"], ["ja-JP"]) in observed


def test_movie_and_whitespace_retry_keep_the_selected_language(
    backend_factory,
    mock_upstream,
):
    backend = backend_factory()
    backend.setup_and_login()
    assert mock_upstream.client.post("/__admin/reset").status_code == 200
    _configure_tmdb(backend, mock_upstream, "jp")

    _activate(mock_upstream, "localized-movie-jp")
    movie = _analyse(backend, mock_upstream, "tmdb-movie.xml")
    assert movie["official_title"] == "ローカライズ映画"
    assert movie["title_raw"] == "Localized Movie"
    assert movie["year"] == 2026
    assert movie["group_name"] == "E2E"

    _activate(mock_upstream, "localized-retry-jp")
    retried = _analyse(backend, mock_upstream, "tmdb-retry.xml")
    assert retried["official_title"] == "再試行アニメ"

    search_requests = [
        request
        for request in _tmdb_requests(mock_upstream)
        if request["path"].startswith("/tmdb/3/search/")
    ]
    assert any(
        request["path"] == "/tmdb/3/search/movie"
        and request["query"]["query"] == ["Localized Movie"]
        and request["query"]["language"] == ["ja-JP"]
        for request in search_requests
    )
    retry_queries = [
        request["query"]["query"][0]
        for request in search_requests
        if request["path"] == "/tmdb/3/search/tv"
        and request["query"]["language"] == ["ja-JP"]
    ]
    assert retry_queries[-2:] == ["Retry Localized Show", "RetryLocalizedShow"]
