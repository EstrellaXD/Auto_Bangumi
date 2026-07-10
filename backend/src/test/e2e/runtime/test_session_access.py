"""Credential-scope and multi-session access-control runtime coverage."""

import pytest

pytestmark = pytest.mark.e2e


def test_api_tokens_reach_data_routes_but_not_account_control(backend_factory):
    backend = backend_factory()
    backend.setup_and_login()

    created = backend.client.post(
        "/api/v1/tokens",
        json={"name": "runtime-api", "scope": "api"},
    )
    assert created.status_code == 201
    api_token = created.json()["token"]

    with backend.new_client(headers={"Authorization": f"Bearer {api_token}"}) as bearer:
        assert bearer.get("/api/v1/status").status_code == 200
        assert bearer.get("/api/v1/config/get").status_code == 200
        assert bearer.get("/api/v1/users").status_code == 403
        assert bearer.get("/api/v1/tokens").status_code == 403
        assert (
            bearer.post(
                "/api/v1/auth/update",
                json={"password": "anotherpassword123"},
            ).status_code
            == 403
        )

    mcp_created = backend.client.post(
        "/api/v1/tokens",
        json={"name": "runtime-mcp", "scope": "mcp"},
    )
    assert mcp_created.status_code == 201
    with backend.new_client(
        headers={"Authorization": f"Bearer {mcp_created.json()['token']}"}
    ) as mcp_bearer:
        assert mcp_bearer.get("/api/v1/status").status_code == 401

    with backend.new_client(
        headers={"Authorization": "Bearer invalid-explicit-token"}
    ) as invalid_header:
        invalid_header.cookies.set("token", backend.client.cookies.get("token"))
        assert invalid_header.get("/api/v1/status").status_code == 401


def test_password_change_rotates_all_browser_sessions(backend_factory):
    backend = backend_factory()
    setup = backend.setup()
    assert setup.status_code == 200
    assert setup.json()["status"] is True

    with backend.new_client() as first, backend.new_client() as second:
        assert backend.login(client=first).status_code == 200
        assert backend.login(client=second).status_code == 200

        created_user = first.post(
            "/api/v1/users",
            json={"username": "seconduser", "password": "secondpassword123"},
        )
        assert created_user.status_code == 201
        assert {user["username"] for user in first.get("/api/v1/users").json()} == {
            "testadmin",
            "seconduser",
        }

        old_second_cookie = second.cookies.get("token")
        changed = first.post(
            "/api/v1/auth/update",
            json={"password": "newpassword123"},
        )
        assert changed.status_code == 200
        assert changed.json() == {"authenticated": True}
        assert first.cookies.get("token")
        assert first.cookies.get("token") != old_second_cookie
        assert first.get("/api/v1/status").status_code == 200
        assert second.get("/api/v1/status").status_code == 401

    with backend.new_client() as old_password, backend.new_client() as new_password:
        assert backend.login(client=old_password).status_code == 401
        assert (
            backend.login(
                client=new_password,
                password="newpassword123",
            ).status_code
            == 200
        )
