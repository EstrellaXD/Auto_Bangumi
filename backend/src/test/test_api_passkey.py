"""Tests for Passkey (WebAuthn) API endpoints."""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from module.api import v1
from module.models import ResponseModel
from module.models.passkey import Passkey
from module.security.api import get_current_user

from test.factories import make_passkey


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    """Create a FastAPI app with v1 routes for testing."""
    app = FastAPI()
    app.include_router(v1, prefix="/api")
    return app


@pytest.fixture
def authed_client(app):
    """TestClient with auth dependency overridden."""

    async def mock_user():
        return "testuser"

    app.dependency_overrides[get_current_user] = mock_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def unauthed_client(app):
    """TestClient without auth (no override)."""
    return TestClient(app)


@pytest.fixture
def mock_webauthn():
    """Mock WebAuthn service."""
    service = MagicMock()
    service.generate_registration_options.return_value = {
        "challenge": "dGVzdF9jaGFsbGVuZ2U",
        "rp": {"name": "AutoBangumi", "id": "localhost"},
        "user": {"id": "dXNlcl9pZA", "name": "testuser", "displayName": "testuser"},
        "pubKeyCredParams": [{"type": "public-key", "alg": -7}],
        "timeout": 60000,
        "attestation": "none",
    }
    service.generate_authentication_options.return_value = {
        "challenge": "dGVzdF9jaGFsbGVuZ2U",
        "timeout": 60000,
        "rpId": "localhost",
        "allowCredentials": [{"type": "public-key", "id": "Y3JlZF9pZA"}],
    }
    service.generate_discoverable_authentication_options.return_value = {
        "challenge": "dGVzdF9jaGFsbGVuZ2U",
        "timeout": 60000,
        "rpId": "localhost",
    }
    mock_passkey = MagicMock()
    mock_passkey.credential_id = "cred_id"
    mock_passkey.public_key = "public_key"
    mock_passkey.sign_count = 0
    mock_passkey.name = "Test Passkey"
    mock_passkey.user_id = 1
    service.verify_registration.return_value = mock_passkey
    service.verify_authentication.return_value = (True, 1)
    return service


@pytest.fixture
def mock_user_model():
    """Mock User model."""
    user = MagicMock()
    user.id = 1
    user.username = "testuser"
    return user


# ---------------------------------------------------------------------------
# Auth requirement
# ---------------------------------------------------------------------------


class TestAuthRequired:
    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_register_options_unauthorized(self, unauthed_client):
        """POST /passkey/register/options without auth returns 401."""
        response = unauthed_client.post("/api/v1/passkey/register/options")
        assert response.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_register_verify_unauthorized(self, unauthed_client):
        """POST /passkey/register/verify without auth returns 401."""
        response = unauthed_client.post(
            "/api/v1/passkey/register/verify",
            json={"name": "Test", "attestation_response": {}},
        )
        assert response.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_list_passkeys_unauthorized(self, unauthed_client):
        """GET /passkey/list without auth returns 401."""
        response = unauthed_client.get("/api/v1/passkey/list")
        assert response.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_delete_passkey_unauthorized(self, unauthed_client):
        """POST /passkey/delete without auth returns 401."""
        response = unauthed_client.post(
            "/api/v1/passkey/delete", json={"passkey_id": 1}
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /passkey/register/options
# ---------------------------------------------------------------------------


class TestRegisterOptions:
    def test_get_registration_options_success(
        self, authed_client, mock_webauthn, mock_user_model
    ):
        """POST /passkey/register/options returns registration options."""
        with patch(
            "module.api.passkey._get_webauthn_from_request", return_value=mock_webauthn
        ):
            with patch("module.api.passkey.async_session_factory") as MockSession:
                mock_session = AsyncMock()
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = mock_user_model
                mock_session.execute = AsyncMock(return_value=mock_result)

                mock_passkey_db = MagicMock()
                mock_passkey_db.get_passkeys_by_user_id = AsyncMock(return_value=[])

                MockSession.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

                with patch(
                    "module.api.passkey.PasskeyDatabase", return_value=mock_passkey_db
                ):
                    response = authed_client.post("/api/v1/passkey/register/options")

        assert response.status_code == 200
        data = response.json()
        assert "challenge" in data
        assert "rp" in data
        assert "user" in data

    def test_get_registration_options_user_not_found(
        self, authed_client, mock_webauthn
    ):
        """POST /passkey/register/options with non-existent user returns 404."""
        with patch(
            "module.api.passkey._get_webauthn_from_request", return_value=mock_webauthn
        ):
            with patch("module.api.passkey.async_session_factory") as MockSession:
                mock_session = AsyncMock()
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = None
                mock_session.execute = AsyncMock(return_value=mock_result)

                MockSession.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

                response = authed_client.post("/api/v1/passkey/register/options")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /passkey/register/verify
# ---------------------------------------------------------------------------


class TestRegisterVerify:
    def test_verify_registration_success(
        self, authed_client, mock_webauthn, mock_user_model
    ):
        """POST /passkey/register/verify successfully registers passkey."""
        with patch(
            "module.api.passkey._get_webauthn_from_request", return_value=mock_webauthn
        ):
            with patch("module.api.passkey.async_session_factory") as MockSession:
                mock_session = AsyncMock()
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = mock_user_model
                mock_session.execute = AsyncMock(return_value=mock_result)

                mock_passkey_db = MagicMock()
                mock_passkey_db.create_passkey = AsyncMock()

                MockSession.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

                with patch(
                    "module.api.passkey.PasskeyDatabase", return_value=mock_passkey_db
                ):
                    response = authed_client.post(
                        "/api/v1/passkey/register/verify",
                        json={
                            "name": "My iPhone",
                            "attestation_response": {
                                "id": "credential_id",
                                "rawId": "raw_id",
                                "response": {
                                    "clientDataJSON": "data",
                                    "attestationObject": "object",
                                },
                                "type": "public-key",
                            },
                        },
                    )

        assert response.status_code == 200
        data = response.json()
        assert "msg_en" in data
        assert "registered successfully" in data["msg_en"]


# ---------------------------------------------------------------------------
# POST /passkey/auth/options (no auth required)
# ---------------------------------------------------------------------------


class TestAuthOptions:
    def test_get_auth_options_with_username(self, unauthed_client, mock_webauthn):
        """POST /passkey/auth/options with username returns auth options."""
        mock_user = MagicMock()
        mock_user.id = 1

        mock_passkeys = [make_passkey()]

        with patch(
            "module.api.passkey._get_webauthn_from_request", return_value=mock_webauthn
        ):
            with patch("module.api.passkey.async_session_factory") as MockSession:
                mock_session = AsyncMock()
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = mock_user
                mock_session.execute = AsyncMock(return_value=mock_result)

                mock_passkey_db = MagicMock()
                mock_passkey_db.get_passkeys_by_user_id = AsyncMock(
                    return_value=mock_passkeys
                )

                MockSession.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

                with patch(
                    "module.api.passkey.PasskeyDatabase", return_value=mock_passkey_db
                ):
                    response = unauthed_client.post(
                        "/api/v1/passkey/auth/options", json={"username": "testuser"}
                    )

        assert response.status_code == 200
        data = response.json()
        assert "challenge" in data

    def test_get_auth_options_discoverable(self, unauthed_client, mock_webauthn):
        """POST /passkey/auth/options without username returns discoverable options."""
        with patch(
            "module.api.passkey._get_webauthn_from_request", return_value=mock_webauthn
        ):
            response = unauthed_client.post(
                "/api/v1/passkey/auth/options", json={"username": None}
            )

        assert response.status_code == 200
        data = response.json()
        assert "challenge" in data

    def test_get_auth_options_user_not_found(self, unauthed_client, mock_webauthn):
        """POST /passkey/auth/options with non-existent user returns 404."""
        with patch(
            "module.api.passkey._get_webauthn_from_request", return_value=mock_webauthn
        ):
            with patch("module.api.passkey.async_session_factory") as MockSession:
                mock_session = AsyncMock()
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = None
                mock_session.execute = AsyncMock(return_value=mock_result)

                MockSession.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

                response = unauthed_client.post(
                    "/api/v1/passkey/auth/options", json={"username": "nonexistent"}
                )

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /passkey/auth/verify (no auth required)
# ---------------------------------------------------------------------------


class TestAuthVerify:
    def test_login_with_passkey_success(self, unauthed_client, mock_webauthn):
        """POST /passkey/auth/verify with valid passkey logs in."""
        mock_response = ResponseModel(
            status=True,
            status_code=200,
            msg_en="OK",
            msg_zh="成功",
            data={"username": "testuser"},
        )
        mock_strategy = MagicMock()
        mock_strategy.authenticate = AsyncMock(return_value=mock_response)

        with patch(
            "module.api.passkey._get_webauthn_from_request", return_value=mock_webauthn
        ):
            with patch(
                "module.api.passkey.PasskeyAuthStrategy", return_value=mock_strategy
            ):
                with patch("module.api.passkey.active_user", []):
                    response = unauthed_client.post(
                        "/api/v1/passkey/auth/verify",
                        json={
                            "username": "testuser",
                            "credential": {
                                "id": "cred_id",
                                "rawId": "raw_id",
                                "response": {
                                    "clientDataJSON": "data",
                                    "authenticatorData": "auth_data",
                                    "signature": "sig",
                                },
                                "type": "public-key",
                            },
                        },
                    )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_login_with_passkey_failure(self, unauthed_client, mock_webauthn):
        """POST /passkey/auth/verify with invalid passkey fails."""
        mock_response = ResponseModel(
            status=False, status_code=401, msg_en="Invalid passkey", msg_zh="无效的凭证"
        )
        mock_strategy = MagicMock()
        mock_strategy.authenticate = AsyncMock(return_value=mock_response)

        with patch(
            "module.api.passkey._get_webauthn_from_request", return_value=mock_webauthn
        ):
            with patch(
                "module.api.passkey.PasskeyAuthStrategy", return_value=mock_strategy
            ):
                response = unauthed_client.post(
                    "/api/v1/passkey/auth/verify",
                    json={
                        "username": "testuser",
                        "credential": {
                            "id": "invalid_cred",
                            "rawId": "raw_id",
                            "response": {
                                "clientDataJSON": "data",
                                "authenticatorData": "auth_data",
                                "signature": "invalid_sig",
                            },
                            "type": "public-key",
                        },
                    },
                )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /passkey/list
# ---------------------------------------------------------------------------


class TestListPasskeys:
    def test_list_passkeys_success(self, authed_client, mock_user_model):
        """GET /passkey/list returns user's passkeys."""
        passkeys = [
            make_passkey(id=1, name="iPhone"),
            make_passkey(id=2, name="MacBook"),
        ]

        with patch("module.api.passkey.async_session_factory") as MockSession:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_user_model
            mock_session.execute = AsyncMock(return_value=mock_result)

            mock_passkey_db = MagicMock()
            mock_passkey_db.get_passkeys_by_user_id = AsyncMock(return_value=passkeys)
            mock_passkey_db.to_list_model = MagicMock(
                side_effect=lambda pk: {
                    "id": pk.id,
                    "name": pk.name,
                    "created_at": pk.created_at.isoformat(),
                    "last_used_at": None,
                    "backup_eligible": pk.backup_eligible,
                    "aaguid": pk.aaguid,
                }
            )

            MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch(
                "module.api.passkey.PasskeyDatabase", return_value=mock_passkey_db
            ):
                response = authed_client.get("/api/v1/passkey/list")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_list_passkeys_empty(self, authed_client, mock_user_model):
        """GET /passkey/list with no passkeys returns empty list."""
        with patch("module.api.passkey.async_session_factory") as MockSession:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_user_model
            mock_session.execute = AsyncMock(return_value=mock_result)

            mock_passkey_db = MagicMock()
            mock_passkey_db.get_passkeys_by_user_id = AsyncMock(return_value=[])

            MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch(
                "module.api.passkey.PasskeyDatabase", return_value=mock_passkey_db
            ):
                response = authed_client.get("/api/v1/passkey/list")

        assert response.status_code == 200
        assert response.json() == []


# ---------------------------------------------------------------------------
# POST /passkey/delete
# ---------------------------------------------------------------------------


class TestDeletePasskey:
    def test_delete_passkey_success(self, authed_client, mock_user_model):
        """POST /passkey/delete successfully deletes passkey."""
        with patch("module.api.passkey.async_session_factory") as MockSession:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_user_model
            mock_session.execute = AsyncMock(return_value=mock_result)

            mock_passkey_db = MagicMock()
            mock_passkey_db.delete_passkey = AsyncMock()

            MockSession.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            MockSession.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch(
                "module.api.passkey.PasskeyDatabase", return_value=mock_passkey_db
            ):
                response = authed_client.post(
                    "/api/v1/passkey/delete", json={"passkey_id": 1}
                )

        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["msg_en"]
