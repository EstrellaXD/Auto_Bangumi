"""Multi-user API and persisted-session integration tests."""

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
async def test_last_enabled_user_conflict_and_api_token_flow(app):
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
        assert (
            await client.delete(f"/api/v1/tokens/{token_id}", headers=headers)
        ).status_code == 204
        assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 401
