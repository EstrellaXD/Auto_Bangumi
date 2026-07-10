"""Tests for database-backed Auth API endpoints."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from module.api import v1
from module.application.auth import AuthenticationError
from module.conf import settings
from module.models.auth import ApiToken
from module.models.user import User
from module.security.api import get_auth_service
from module.security.jwt import create_access_token


@pytest.fixture
def service():
    service = MagicMock()
    service.login = AsyncMock()
    service.authenticate_api_token = AsyncMock(return_value=None)
    service.authenticate_session = AsyncMock(return_value=None)
    service.refresh_session = AsyncMock()
    service.logout = AsyncMock(return_value=True)
    service.get_user = AsyncMock()
    service.update_current_user = AsyncMock()
    service.create_api_token_for_user_id = AsyncMock()
    return service


@pytest.fixture
def app(service):
    app = FastAPI()
    app.include_router(v1, prefix="/api")
    app.dependency_overrides[get_auth_service] = lambda: service
    return app


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def persisted_user(username: str = "testuser") -> User:
    return User(id=1, username=username, password="hashed-password", enabled=True)


class TestLogin:
    def test_login_success_sets_persisted_session_cookie(self, client, service):
        service.login.return_value = (persisted_user(), "persisted-session")
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "test-password"},
        )
        assert response.status_code == 200
        assert response.json() == {"authenticated": True}
        assert "persisted-session" not in response.text
        assert response.cookies.get("token") == "persisted-session"

    def test_login_failure_is_unauthorized(self, client, service):
        service.login.side_effect = AuthenticationError("invalid")
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "wrong-password"},
        )
        assert response.status_code == 401


class TestRefresh:
    def test_post_refresh_extends_database_session(self, client, service):
        service.refresh_session.return_value = persisted_user()
        client.cookies.set("token", "persisted-session")
        response = client.post("/api/v1/auth/refresh_token")
        assert response.status_code == 200
        assert response.json() == {"authenticated": True}
        assert "persisted-session" not in response.text

    def test_get_refresh_is_deprecated_compatibility_alias(self, client, service):
        service.refresh_session.return_value = persisted_user()
        client.cookies.set("token", "persisted-session")
        response = client.get("/api/v1/auth/refresh_token")
        assert response.status_code == 200
        assert response.json() == {"authenticated": True}
        assert "persisted-session" not in response.text
        assert response.headers["deprecation"] == "true"

    def test_refresh_rejects_legacy_jwt(self, client, service):
        service.refresh_session.return_value = None
        legacy_jwt = create_access_token(
            {"sub": "testuser"}, expires_delta=timedelta(hours=1)
        )
        client.cookies.set("token", legacy_jwt)
        response = client.post("/api/v1/auth/refresh_token")
        assert response.status_code == 401
        service.refresh_session.assert_awaited_once_with(legacy_jwt)

    def test_refresh_without_cookie_is_unauthorized(self, client):
        assert client.post("/api/v1/auth/refresh_token").status_code == 401


def test_logout_is_idempotent_and_revokes_cookie_session(client, service):
    client.cookies.set("token", "persisted-session")
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    service.logout.assert_awaited_once_with("persisted-session")
    assert response.cookies.get("token") is None
    assert "token=" in response.headers["set-cookie"]
    assert "Max-Age=0" in response.headers["set-cookie"]


def test_update_rotates_all_sessions_without_returning_secret(client, service):
    service.authenticate_session.return_value = persisted_user()
    service.update_current_user.return_value = (
        persisted_user("renamed_user"),
        "rotated-session",
    )
    client.cookies.set("token", "persisted-session")
    response = client.post(
        "/api/v1/auth/update",
        json={"username": "renamed_user", "password": "new-password"},
    )
    assert response.status_code == 200
    assert response.json() == {"authenticated": True}
    assert "rotated-session" not in response.text
    assert response.cookies.get("token") == "rotated-session"
    service.update_current_user.assert_awaited_once()
    assert service.update_current_user.await_args.args[0] == 1


def test_me_returns_the_authenticated_principal_without_username_lookup(
    client, service
):
    service.authenticate_session.return_value = persisted_user("stable_user")
    client.cookies.set("token", "persisted-session")

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["username"] == "stable_user"
    service.get_user.assert_not_awaited()


def test_token_creation_uses_the_principal_user_id(client, service):
    service.authenticate_session.return_value = persisted_user("stale_username")
    service.create_api_token_for_user_id.return_value = (
        ApiToken(
            id=7,
            user_id=1,
            name="automation",
            scope="api",
            token_hash="a" * 64,
            prefix="ab_api_abcde",
            created_at=datetime.now(timezone.utc),
        ),
        "ab_api_one_time_secret",
    )
    client.cookies.set("token", "persisted-session")

    response = client.post(
        "/api/v1/tokens", json={"name": "automation", "scope": "api"}
    )

    assert response.status_code == 201
    service.create_api_token_for_user_id.assert_awaited_once_with(
        1,
        name="automation",
        scope="api",
        expires_at=None,
    )


def test_update_rejects_enabled_field(client, service):
    service.authenticate_session.return_value = persisted_user()
    client.cookies.set("token", "persisted-session")
    response = client.post("/api/v1/auth/update", json={"enabled": False})
    assert response.status_code == 422


@patch("module.security.api.DEV_AUTH_BYPASS", False)
def test_authorization_does_not_accept_a_browser_session(client, service):
    service.authenticate_api_token.return_value = None
    service.authenticate_session.return_value = persisted_user()
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer persisted-session"},
    )
    assert response.status_code == 401
    service.authenticate_api_token.assert_awaited_once_with(
        "persisted-session", scope="api"
    )
    service.authenticate_session.assert_not_awaited()


@patch("module.security.api.DEV_AUTH_BYPASS", False)
def test_authorization_does_not_accept_plaintext_config_token(client, service):
    service.authenticate_api_token.return_value = None
    with patch.object(settings.security, "login_tokens", ["legacy-plaintext-token"]):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer legacy-plaintext-token"},
        )
    assert response.status_code == 401


@patch("module.security.api.DEV_AUTH_BYPASS", False)
def test_legacy_jwt_cookie_is_not_normal_authentication(client, service):
    legacy_jwt = create_access_token(
        {"sub": "testuser"}, expires_delta=timedelta(hours=1)
    )
    service.authenticate_session.return_value = None
    client.cookies.set("token", legacy_jwt)
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


@patch("module.security.api.DEV_AUTH_BYPASS", False)
def test_me_requires_authentication(client):
    assert client.get("/api/v1/auth/me").status_code == 401
