"""Contract tests for the hermetic qBittorrent HTTP fake."""

import runpy
import threading
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.e2e


SERVER_PATH = Path(__file__).resolve().parents[5] / "e2e" / "fake-qb" / "server.py"
SERVER_MODULE = runpy.run_path(str(SERVER_PATH))
create_server = SERVER_MODULE["create_server"]
MATCHING_HASH = SERVER_MODULE["MATCHING_HASH"]
NEIGHBOUR_HASH = SERVER_MODULE["NEIGHBOUR_HASH"]
DELETE_FAILURE_HASH = SERVER_MODULE["DELETE_FAILURE_HASH"]


@pytest.fixture
def fake_qb_url():
    server = create_server("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def login(client: httpx.Client) -> None:
    response = client.post(
        "/api/v2/auth/login",
        data={"username": "admin", "password": "adminadmin"},
    )
    assert response.status_code == 200
    assert response.text == "Ok."


def test_qb_endpoints_and_successful_delete_update_state(fake_qb_url):
    with httpx.Client(base_url=fake_qb_url) as client:
        login(client)

        assert client.get("/api/v2/app/version").text == "v5.2.3"
        preferences = client.get("/api/v2/app/preferences").json()
        assert preferences["save_path"] == "D:\\Downloads\\Bangumi"
        assert {key: preferences[key] for key in ("dht", "pex", "lsd", "upnp")} == {
            "dht": False,
            "pex": False,
            "lsd": False,
            "upnp": False,
        }

        torrents = client.get("/api/v2/torrents/info").json()
        by_hash = {torrent["hash"]: torrent for torrent in torrents}
        assert by_hash[MATCHING_HASH]["save_path"].endswith("Season 1\\")
        assert by_hash[NEIGHBOUR_HASH]["save_path"].endswith("Season 10")

        response = client.post(
            "/api/v2/torrents/delete",
            data={"hashes": MATCHING_HASH, "deleteFiles": "true"},
        )
        assert response.status_code == 200

        state = client.get("/__admin/state").json()
        remaining = {torrent["hash"] for torrent in state["torrents"]}
        assert MATCHING_HASH not in remaining
        assert NEIGHBOUR_HASH in remaining

        assert client.post("/api/v2/auth/logout").status_code == 200
        assert client.get("/api/v2/torrents/info").status_code == 403


def test_torrent_presets_include_webui_fields(fake_qb_url):
    with httpx.Client(base_url=fake_qb_url) as client:
        login(client)

        torrent = client.get("/api/v2/torrents/info").json()[0]

    assert {
        "hash",
        "name",
        "size",
        "progress",
        "dlspeed",
        "upspeed",
        "num_seeds",
        "num_leechs",
        "state",
        "eta",
        "category",
        "save_path",
        "added_on",
    } <= torrent.keys()


def test_forced_delete_failure_is_atomic(fake_qb_url):
    with httpx.Client(base_url=fake_qb_url) as client:
        login(client)

        response = client.post(
            "/api/v2/torrents/delete",
            data={
                "hashes": f"{MATCHING_HASH}|{DELETE_FAILURE_HASH}",
                "deleteFiles": "false",
            },
        )
        assert response.status_code == 500

        state = client.get("/__admin/state").json()
        remaining = {torrent["hash"] for torrent in state["torrents"]}
        assert MATCHING_HASH in remaining
        assert DELETE_FAILURE_HASH in remaining


def test_request_journal_preserves_form_shape_and_redacts_secrets(fake_qb_url):
    with httpx.Client(base_url=fake_qb_url) as client:
        login(client)

        response = client.post(
            "/api/v2/unsupported?token=query-secret&plain=query-value",
            data={
                "hashes": [MATCHING_HASH, NEIGHBOUR_HASH],
                "password": "form-secret",
                "auth_token": "form-token",
                "plain": "form-value",
            },
            headers={
                "Authorization": "Bearer header-secret",
                "X-Api-Token": "header-token",
            },
        )
        assert response.status_code == 501

        journal = client.get("/__admin/requests").json()["requests"]
        login_request = journal[0]
        assert login_request["form"] == {
            "username": ["admin"],
            "password": ["[REDACTED]"],
        }

        unsupported = journal[-1]
        assert unsupported["query"] == {
            "token": ["[REDACTED]"],
            "plain": ["query-value"],
        }
        assert unsupported["form"] == {
            "hashes": [MATCHING_HASH, NEIGHBOUR_HASH],
            "password": ["[REDACTED]"],
            "auth_token": ["[REDACTED]"],
            "plain": ["form-value"],
        }
        assert unsupported["headers"]["Authorization"] == "[REDACTED]"
        assert unsupported["headers"]["Cookie"] == "[REDACTED]"
        assert unsupported["headers"]["X-Api-Token"] == "[REDACTED]"


def test_admin_reset_restores_presets_and_clears_journal(fake_qb_url):
    with httpx.Client(base_url=fake_qb_url) as client:
        login(client)
        client.post(
            "/api/v2/torrents/delete",
            data={"hashes": MATCHING_HASH, "deleteFiles": "true"},
        )

        response = client.post("/__admin/reset")
        assert response.status_code == 200
        assert response.json() == {"ok": True}

        state = client.get("/__admin/state").json()
        hashes = {torrent["hash"] for torrent in state["torrents"]}
        assert {MATCHING_HASH, NEIGHBOUR_HASH, DELETE_FAILURE_HASH} <= hashes
        assert client.get("/__admin/requests").json() == {"requests": []}
