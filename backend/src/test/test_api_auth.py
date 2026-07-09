"""Tests for database-backed Auth API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from module.api import v1
from module.application.auth import AuthenticationError
from module.models.user import User
from module.security.api import get_auth_service, get_current_user


@pytest.fixture
def service():
    service = MagicMock()
    service.login = AsyncMock()
    service.refresh_session = AsyncMock()
    service.exchange_legacy_jwt = AsyncMock()
    service.logout = AsyncMock(return_value=True)
    service.get_user = AsyncMock()
    service.update_current_user = AsyncMock()
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
        assert response.json() == {
            "access_token": "persisted-session",
            "token_type": "bearer",
        }
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
        assert response.json()["access_token"] == "persisted-session"

    def test_get_refresh_is_deprecated_compatibility_alias(self, client, service):
        service.refresh_session.return_value = persisted_user()
        client.cookies.set("token", "persisted-session")
        response = client.get("/api/v1/auth/refresh_token")
        assert response.status_code == 200
        assert response.headers["deprecation"] == "true"

    def test_refresh_exchanges_legacy_jwt(self, client, service):
        service.refresh_session.return_value = None
        service.exchange_legacy_jwt.return_value = (
            persisted_user(),
            "new-persisted-session",
        )
        client.cookies.set("token", "legacy-jwt")
        response = client.post("/api/v1/auth/refresh_token")
        assert response.status_code == 200
        assert response.json()["access_token"] == "new-persisted-session"

    def test_refresh_without_cookie_is_unauthorized(self, client):
        assert client.post("/api/v1/auth/refresh_token").status_code == 401


def test_logout_is_idempotent_and_revokes_cookie_session(client, service):
    client.cookies.set("token", "persisted-session")
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    service.logout.assert_awaited_once_with("persisted-session")
    assert response.cookies.get("token") is None


def test_update_rotates_all_sessions(client, app, service):
    async def current_user():
        return "testuser"

    app.dependency_overrides[get_current_user] = current_user
    service.update_current_user.return_value = (
        persisted_user("renamed_user"),
        "rotated-session",
    )
    response = client.post(
        "/api/v1/auth/update",
        json={"username": "renamed_user", "password": "new-password"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"] == "rotated-session"


@patch("module.security.api.DEV_AUTH_BYPASS", False)
def test_me_requires_authentication(client):
    assert client.get("/api/v1/auth/me").status_code == 401
