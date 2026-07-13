"""Durable data and credential revocation across real process restarts."""

from typing import Any

import pytest

pytestmark = pytest.mark.e2e


def test_restart_preserves_domain_data_and_never_revives_revoked_credentials(
    backend_factory,
    mock_upstream,
):
    backend = backend_factory()
    backend.setup_and_login()

    def local_only(config: dict[str, Any]) -> None:
        config["network"]["tmdb_base_url"] = f"{mock_upstream.base_url}/tmdb"
        config["network"]["bgm_base_url"] = f"{mock_upstream.base_url}/bgm"
        config["update"]["auto_check"] = False

    backend.update_config(local_only)
    backend.stop()
    backend.seed_database(
        {
            "bangumi": [
                {
                    "id": 41,
                    "official_title": "Persistent Anime",
                    "title_raw": "Persistent Anime",
                    "save_path": "/downloads/Bangumi/Persistent Anime (2026)/Season 1",
                }
            ]
        }
    )
    backend.start()
    backend.stop_tasks()

    created_user = backend.client.post(
        "/api/v1/users",
        json={"username": "persistuser", "password": "persistpassword123"},
    )
    assert created_user.status_code == 201

    created_token = backend.client.post(
        "/api/v1/tokens",
        json={"name": "restart-token", "scope": "api"},
    )
    assert created_token.status_code == 201
    token_id = created_token.json()["id"]
    raw_token = created_token.json()["token"]

    added_rss = backend.client.post(
        "/api/v1/rss/add",
        json={
            "name": "Persistent RSS",
            "url": f"{mock_upstream.base_url}/rss/tmdb-tv.xml",
            "aggregate": True,
            "parser": "tmdb",
            "enabled": True,
        },
    )
    assert added_rss.status_code == 200

    persisted_cookie = backend.client.cookies.get("token")
    backend.restart()
    backend.stop_tasks()

    assert backend.client.get("/api/v1/status").status_code == 200
    users = backend.client.get("/api/v1/users")
    assert users.status_code == 200
    assert {user["username"] for user in users.json()} == {
        "testadmin",
        "persistuser",
    }
    rss_items = backend.client.get("/api/v1/rss")
    assert rss_items.status_code == 200
    assert [(item["name"], item["url"]) for item in rss_items.json()] == [
        ("Persistent RSS", f"{mock_upstream.base_url}/rss/tmdb-tv.xml")
    ]
    bangumi = backend.client.get("/api/v1/bangumi/get/41")
    assert bangumi.status_code == 200
    assert bangumi.json()["official_title"] == "Persistent Anime"

    with backend.new_client(headers={"Authorization": f"Bearer {raw_token}"}) as bearer:
        assert bearer.get("/api/v1/status").status_code == 200

    revoked_token = backend.client.delete(f"/api/v1/tokens/{token_id}")
    assert revoked_token.status_code == 204
    logout = backend.client.post("/api/v1/auth/logout")
    assert logout.status_code == 200
    backend.restart()

    with backend.new_client(
        headers={"Authorization": f"Bearer {raw_token}"}
    ) as revoked_bearer:
        assert revoked_bearer.get("/api/v1/status").status_code == 401

    with backend.new_client() as revoked_session:
        revoked_session.cookies.set("token", persisted_cookie)
        assert revoked_session.get("/api/v1/status").status_code == 401

    assert backend.login().status_code == 200
    backend.stop_tasks()
    assert backend.client.get("/api/v1/bangumi/get/41").status_code == 200
    assert backend.client.get("/api/v1/rss").status_code == 200
