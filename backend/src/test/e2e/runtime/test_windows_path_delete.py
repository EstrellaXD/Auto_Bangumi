"""Windows save-path matching through the public delete/disable APIs."""

from typing import Any

import pytest

pytestmark = pytest.mark.e2e

MATCHING_HASH = "a" * 40
NEIGHBOUR_HASH = "b" * 40
DELETE_FAILURE_HASH = "f" * 40


def _configure_local_network(backend, fake_qb) -> None:
    def mutate(config: dict[str, Any]) -> None:
        config["network"]["tmdb_base_url"] = f"{fake_qb.base_url}/tmdb"
        config["network"]["bgm_base_url"] = f"{fake_qb.base_url}/bgm"
        config["update"]["auto_check"] = False

    backend.update_config(mutate)


def _prepare_backend(backend_factory, fake_qb, bangumi: dict[str, Any]):
    assert fake_qb.client.post("/__admin/reset").status_code == 200
    backend = backend_factory()
    backend.setup_and_login(
        downloader_type="qbittorrent",
        downloader_host=fake_qb.base_url,
        downloader_username="admin",
        downloader_password="adminadmin",
        downloader_path="D:/Downloads/Bangumi",
    )
    _configure_local_network(backend, fake_qb)

    backend.stop()
    backend.seed_database({"bangumi": [bangumi]})
    backend.start()
    backend.stop_tasks()
    assert fake_qb.client.post("/__admin/reset").status_code == 200
    return backend


@pytest.mark.parametrize("action", ["delete", "disable"])
def test_windows_separator_normalization_deletes_only_the_exact_season(
    backend_factory,
    fake_qb,
    action,
):
    backend = _prepare_backend(
        backend_factory,
        fake_qb,
        {
            "id": 1,
            "official_title": "Test Anime",
            "title_raw": "Test Anime",
            "year": "2024",
            "save_path": "D:/Downloads/Bangumi/Test Anime (2024)/Season 1",
        },
    )

    if action == "delete":
        response = backend.client.delete("/api/v1/bangumi/delete/1?file=true")
    else:
        response = backend.client.post("/api/v1/bangumi/disable/1?file=true")
    assert response.status_code == 200, response.text

    state = fake_qb.client.get("/__admin/state").json()
    remaining_hashes = {torrent["hash"] for torrent in state["torrents"]}
    assert MATCHING_HASH not in remaining_hashes
    assert NEIGHBOUR_HASH in remaining_hashes
    assert DELETE_FAILURE_HASH in remaining_hashes

    requests = fake_qb.client.get("/__admin/requests").json()["requests"]
    delete_requests = [
        request for request in requests if request["path"] == "/api/v2/torrents/delete"
    ]
    assert len(delete_requests) == 1
    assert delete_requests[0]["form"] == {
        "hashes": [MATCHING_HASH],
        "deleteFiles": ["true"],
    }

    if action == "disable":
        stored = backend.client.get("/api/v1/bangumi/get/1")
        assert stored.status_code == 200
        assert stored.json()["deleted"] is True


def test_qb_delete_failure_is_reported_without_removing_neighbouring_torrents(
    backend_factory,
    fake_qb,
):
    backend = _prepare_backend(
        backend_factory,
        fake_qb,
        {
            "id": 2,
            "official_title": "Delete Failure",
            "title_raw": "Delete Failure",
            "save_path": "D:/Downloads/Bangumi/Delete Failure/Season 1",
        },
    )

    response = backend.client.delete("/api/v1/bangumi/delete/2?file=true")
    assert response.status_code == 500
    assert "deleting its torrents failed" in response.json()["msg_en"]

    state = fake_qb.client.get("/__admin/state").json()
    remaining_hashes = {torrent["hash"] for torrent in state["torrents"]}
    assert {MATCHING_HASH, NEIGHBOUR_HASH, DELETE_FAILURE_HASH} <= remaining_hashes

    requests = fake_qb.client.get("/__admin/requests").json()["requests"]
    delete_requests = [
        request for request in requests if request["path"] == "/api/v2/torrents/delete"
    ]
    assert len(delete_requests) == 1
    assert delete_requests[0]["form"]["hashes"] == [DELETE_FAILURE_HASH]
