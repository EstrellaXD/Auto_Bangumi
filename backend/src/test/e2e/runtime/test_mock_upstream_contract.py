"""Contract tests for the hermetic mock-upstream HTTP service."""

import importlib.util
import json
import shutil
import threading
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.e2e

REPO_ROOT = Path(__file__).resolve().parents[5]
SERVER_PATH = REPO_ROOT / "e2e" / "mock-upstream" / "server.py"


def _load_create_server():
    spec = importlib.util.spec_from_file_location("e2e_mock_upstream", SERVER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load mock-upstream from {SERVER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.create_server


@pytest.fixture
def fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "fixtures"
    shutil.copytree(REPO_ROOT / "e2e" / "fixtures", root)
    images = root / "images"
    images.mkdir()
    (images / "poster.jpg").write_bytes(b"mock-poster-bytes")
    return root


@pytest.fixture
def upstream(fixture_root: Path):
    server = _load_create_server()("127.0.0.1", 0, fixture_root)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    with httpx.Client(base_url=f"http://{host}:{port}", timeout=5.0) as client:
        yield client, fixture_root
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
    assert not thread.is_alive()


def _activate(client: httpx.Client, name: str) -> None:
    response = client.put(f"/__admin/scenario/{name}")
    assert response.status_code == 200
    assert response.json()["scenario"] == name


def test_health_and_admin_lifecycle(upstream):
    client, _ = upstream

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    response = client.post("/__admin/reset")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert client.get("/__admin/requests").json() == {"requests": []}

    _activate(client, "localized-tv-zh")
    state = client.get("/__admin/state").json()
    assert state == {
        "scenario": "localized-tv-zh",
        "notifications": [],
        "request_count": 0,
    }

    missing = client.put("/__admin/scenario/does-not-exist")
    assert missing.status_code == 404
    assert client.get("/__admin/state").json()["scenario"] == "localized-tv-zh"

    reset = client.post("/__admin/reset")
    assert reset.status_code == 200
    assert client.get("/__admin/state").json() == {
        "scenario": None,
        "notifications": [],
        "request_count": 0,
    }


def test_tmdb_tv_movie_and_retry_scenarios(upstream):
    client, _ = upstream
    client.post("/__admin/reset")

    _activate(client, "localized-tv-zh")
    tv = client.get(
        "/tmdb/3/search/tv",
        params={
            "query": "Localized Show",
            "language": "zh-CN",
            "api_key": "tmdb-secret",
        },
    )
    assert tv.status_code == 200
    assert tv.json()["results"][0]["name"] == "本地化动画"

    wrong_language = client.get(
        "/tmdb/3/search/tv",
        params={"query": "Localized Show", "language": "en-US"},
    )
    assert wrong_language.status_code == 200
    assert wrong_language.json() == {"results": []}

    detail = client.get(
        "/tmdb/3/tv/1001",
        params={"language": "zh-CN", "api_key": "tmdb-secret"},
    )
    assert detail.status_code == 200
    assert detail.json()["genres"] == [{"id": 16, "name": "Animation"}]
    assert (
        client.get("/tmdb/3/tv/1001", params={"language": "en-US"}).status_code == 404
    )

    season = client.get(
        "/tmdb/3/tv/1001/season/1",
        params={"language": "zh-CN", "api_key": "tmdb-secret"},
    )
    assert season.status_code == 200
    assert season.json()["episodes"][0] == {
        "episode_number": 1,
        "air_date": "2026-07-01",
    }
    assert (
        client.get("/tmdb/3/tv/1001/season/1", params={"language": "en-US"}).status_code
        == 404
    )

    _activate(client, "localized-movie-jp")
    movie = client.get(
        "/tmdb/3/search/movie",
        params={"query": "Localized Movie", "language": "ja-JP"},
    )
    assert movie.status_code == 200
    assert movie.json()["results"][0]["title"] == "ローカライズ映画"
    assert client.get(
        "/tmdb/3/search/tv",
        params={"query": "Localized Movie", "language": "ja-JP"},
    ).json() == {"results": []}

    _activate(client, "localized-retry-jp")
    initial = client.get(
        "/tmdb/3/search/tv",
        params={"query": "Retry Localized Show", "language": "ja-JP"},
    )
    retried = client.get(
        "/tmdb/3/search/tv",
        params={"query": "RetryLocalizedShow", "language": "ja-JP"},
    )
    assert initial.json() == {"results": []}
    assert retried.json()["results"][0]["name"] == "再試行アニメ"


def test_static_routes_head_and_single_ranges(upstream):
    client, fixture_root = upstream
    media = (fixture_root / "files" / "tiny-media.mkv").read_bytes()

    rss = client.get("/rss/tmdb-tv.xml")
    assert rss.status_code == 200
    assert rss.headers["content-type"].startswith("application/rss+xml")
    assert b"Localized Show" in rss.content

    image = client.get("/images/poster.jpg")
    assert image.status_code == 200
    assert image.content == b"mock-poster-bytes"

    player = client.get("/player")
    assert player.status_code == 200
    assert player.headers["content-type"].startswith("text/html")

    torrent = client.get("/torrents/tiny-media.torrent")
    assert torrent.status_code == 200
    assert torrent.headers["content-type"].startswith("application/x-bittorrent")

    head = client.head("/files/tiny-media.mkv")
    assert head.status_code == 200
    assert head.content == b""
    assert int(head.headers["content-length"]) == len(media)
    assert head.headers["accept-ranges"] == "bytes"

    partial = client.get("/files/tiny-media.mkv", headers={"Range": "bytes=7-23"})
    assert partial.status_code == 206
    assert partial.content == media[7:24]
    assert partial.headers["content-range"] == f"bytes 7-23/{len(media)}"
    assert partial.headers["content-length"] == "17"

    suffix = client.get("/files/tiny-media.mkv", headers={"Range": "bytes=-11"})
    assert suffix.status_code == 206
    assert suffix.content == media[-11:]

    unsatisfiable = client.get(
        "/files/tiny-media.mkv", headers={"Range": f"bytes={len(media)}-"}
    )
    assert unsatisfiable.status_code == 416
    assert unsatisfiable.headers["content-range"] == f"bytes */{len(media)}"
    assert unsatisfiable.content == b""

    multiple = client.get("/files/tiny-media.mkv", headers={"Range": "bytes=0-1,4-5"})
    assert multiple.status_code == 416


def test_notification_capture_and_journal_redact_secrets(upstream):
    client, _ = upstream
    client.post("/__admin/reset")

    response = client.post(
        "/notifications/webhook",
        params={"token": "query-secret", "message": "visible-query"},
        headers={
            "Authorization": "Bearer header-secret",
            "Cookie": "session=cookie-secret",
            "X-Api-Key": "header-api-secret",
        },
        json={
            "message": "visible-body",
            "password": "body-password",
            "nested": {"api_token": "body-token", "value": "kept"},
        },
    )
    assert response.status_code == 204

    form_response = client.post(
        "/notifications/form",
        data={"password": "form-password", "message": "visible-form"},
    )
    assert form_response.status_code == 204

    requests = client.get("/__admin/requests").json()["requests"]
    webhook = requests[0]
    assert webhook["path"] == "/notifications/webhook"
    assert webhook["query"] == {
        "token": ["[REDACTED]"],
        "message": ["visible-query"],
    }
    assert webhook["headers"]["authorization"] == "[REDACTED]"
    assert webhook["headers"]["cookie"] == "[REDACTED]"
    assert webhook["headers"]["x-api-key"] == "[REDACTED]"
    assert webhook["body"] == {
        "message": "visible-body",
        "password": "[REDACTED]",
        "nested": {"api_token": "[REDACTED]", "value": "kept"},
    }
    assert requests[1]["body"] == {
        "password": ["[REDACTED]"],
        "message": ["visible-form"],
    }

    state = client.get("/__admin/state").json()
    assert len(state["notifications"]) == 2
    serialized = json.dumps({"requests": requests, "state": state}, ensure_ascii=False)
    for secret in (
        "query-secret",
        "header-secret",
        "cookie-secret",
        "header-api-secret",
        "body-password",
        "body-token",
        "form-password",
    ):
        assert secret not in serialized
    assert "visible-body" in serialized
    assert "visible-form" in serialized


def test_unknown_route_returns_501_and_is_journaled(upstream):
    client, _ = upstream
    client.post("/__admin/reset")

    response = client.get("/not-a-contract-route", params={"api_key": "must-not-leak"})

    assert response.status_code == 501
    journal = client.get("/__admin/requests").json()["requests"]
    assert len(journal) == 1
    assert journal[0]["path"] == "/not-a-contract-route"
    assert journal[0]["query"]["api_key"] == ["[REDACTED]"]
    assert journal[0]["response_status"] == 501
    assert "must-not-leak" not in json.dumps(journal)
