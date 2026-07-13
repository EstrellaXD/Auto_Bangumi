"""Multi-user API and persisted-session integration tests."""

from typing import Any

import httpx
import pytest

from module.database import Database


@pytest.mark.asyncio
async def test_multiple_users_and_sessions_survive_client_recreation(app):
    async with Database() as db:
        await db.user.create_user("first_user", "first-password")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            data={"username": "first_user", "password": "first-password"},
        )
        assert login.status_code == 200
        persisted_cookie = client.cookies.get("token")
        assert persisted_cookie

        created = await client.post(
            "/api/v1/users",
            json={"username": "second_user", "password": "second-password"},
        )
        assert created.status_code == 201
        users = await client.get("/api/v1/users")
        assert {user["username"] for user in users.json()} == {
            "first_user",
            "second_user",
        }

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("token", persisted_cookie)
        me = await client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["username"] == "first_user"
        assert (await client.post("/api/v1/auth/logout")).status_code == 200
        assert (await client.get("/api/v1/auth/me")).status_code == 401


@pytest.mark.asyncio
async def test_last_enabled_user_conflict_and_session_only_route_matrix(app):
    async with Database() as db:
        only = await db.user.create_user("only_user", "only-password")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (
            await client.post(
                "/api/v1/auth/login",
                data={"username": "only_user", "password": "only-password"},
            )
        ).status_code == 200
        browser_session = client.cookies.get("token")
        assert browser_session
        assert (
            await client.patch(f"/api/v1/users/{only.id}", json={"enabled": False})
        ).status_code == 409

        created = await client.post(
            "/api/v1/tokens", json={"name": "automation", "scope": "api"}
        )
        assert created.status_code == 201
        raw_token = created.json()["token"]
        listed = await client.get("/api/v1/tokens")
        assert "token" not in listed.json()[0]
        token_id = listed.json()[0]["id"]

    headers = {"Authorization": f"Bearer {raw_token}"}
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 200
        session_only_requests: list[tuple[str, str, dict[str, Any]]] = [
            ("GET", "/api/v1/users", {}),
            (
                "POST",
                "/api/v1/users",
                {"json": {"username": "third_user", "password": "third-password"}},
            ),
            (
                "PATCH",
                f"/api/v1/users/{only.id}",
                {"json": {"password": "changed-password"}},
            ),
            ("DELETE", f"/api/v1/users/{only.id}", {}),
            ("GET", "/api/v1/tokens", {}),
            (
                "POST",
                "/api/v1/tokens",
                {"json": {"name": "forbidden", "scope": "api"}},
            ),
            ("DELETE", f"/api/v1/tokens/{token_id}", {}),
            (
                "POST",
                "/api/v1/auth/update",
                {"json": {"password": "changed-password"}},
            ),
            ("POST", "/api/v1/passkey/register/options", {}),
            (
                "POST",
                "/api/v1/passkey/register/verify",
                {"json": {"name": "key", "attestation_response": {}}},
            ),
            ("GET", "/api/v1/passkey/list", {}),
            (
                "POST",
                "/api/v1/passkey/delete",
                {"json": {"passkey_id": 1}},
            ),
        ]
        for method, path, request_kwargs in session_only_requests:
            response = await client.request(
                method, path, headers=headers, **request_kwargs
            )
            assert response.status_code == 403, (method, path, response.text)

        # Explicit Authorization takes precedence over a valid cookie and must
        # not silently inherit the cookie session's stronger account authority.
        client.cookies.set("token", browser_session)
        assert (await client.get("/api/v1/tokens", headers=headers)).status_code == 403

        # A browser session token is not a supported Authorization credential.
        client.cookies.clear()
        assert (
            await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {browser_session}"},
            )
        ).status_code == 401

        # Cookie sessions retain account-control authority.
        client.cookies.set("token", browser_session)
        assert (await client.delete(f"/api/v1/tokens/{token_id}")).status_code == 204
        client.cookies.clear()
        assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 401
