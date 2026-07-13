"""Offset-review decisions from persisted torrents and a real TMDB HTTP fake."""

from typing import Any

import pytest

pytestmark = pytest.mark.e2e

ISSUE_1072_TITLE = (
    "[SubsPlease] Haibara-kun no Tsuyokute Seishun New Game - 06v2 "
    "(1080p) [E931DD98].mkv"
)
OVERFLOW_TITLE = (
    "[SubsPlease] Haibara-kun no Tsuyokute Seishun New Game - 13 "
    "(1080p) [ABCDEF12].mkv"
)
CRC_ONLY_TITLE = "[SubsPlease] CRC Only Anime (1080p) [E931DD98].mkv"


def _configure_local_network(backend, upstream) -> None:
    def mutate(config: dict[str, Any]) -> None:
        config["network"]["tmdb_base_url"] = f"{upstream.base_url}/tmdb"
        config["network"]["bgm_base_url"] = f"{upstream.base_url}/bgm"
        config["rss_parser"]["language"] = "zh"
        config["update"]["auto_check"] = False

    backend.update_config(mutate)


@pytest.mark.parametrize(
    ("torrent_title", "expected_flagged", "expected_reason_parts"),
    [
        pytest.param(ISSUE_1072_TITLE, False, (), id="versioned-episode-not-crc"),
        pytest.param(OVERFLOW_TITLE, True, ("13", "12"), id="real-overflow"),
        pytest.param(CRC_ONLY_TITLE, False, (), id="crc-without-episode-signal"),
    ],
)
def test_offset_review_uses_only_real_episode_signals(
    backend_factory,
    twelve_episode_upstream,
    torrent_title,
    expected_flagged,
    expected_reason_parts,
):
    upstream = twelve_episode_upstream
    backend = backend_factory()
    backend.setup_and_login()
    _configure_local_network(backend, upstream)
    activated = upstream.client.put("/__admin/scenario/localized-tv-zh")
    assert activated.status_code == 200

    backend.stop()
    backend.seed_database(
        {
            "bangumi": [
                {
                    "id": 72,
                    "official_title": "Localized Show",
                    "title_raw": "Haibara-kun no Tsuyokute Seishun New Game",
                    "season": 1,
                }
            ],
            "torrents": [
                {
                    "id": 720,
                    "refer_id": 72,
                    "name": torrent_title,
                    "url": "https://fixture.invalid/offset-review.torrent",
                    "downloaded": True,
                }
            ],
        }
    )

    flagged = backend.run_offset_scan(72)
    assert flagged is expected_flagged
    backend.start()
    backend.stop_tasks()

    response = backend.client.get("/api/v1/bangumi/needs-review")
    assert response.status_code == 200
    reviews = response.json()
    if expected_flagged:
        assert [item["id"] for item in reviews] == [72]
        reason = reviews[0]["needs_review_reason"]
        assert all(part in reason for part in expected_reason_parts)
    else:
        assert reviews == []

    journal = upstream.client.get("/__admin/requests").json()["requests"]
    tmdb_requests = [
        request for request in journal if request["path"].startswith("/tmdb/")
    ]
    assert tmdb_requests
    assert all(
        request["query"].get("language") == ["zh-CN"] for request in tmdb_requests
    )
