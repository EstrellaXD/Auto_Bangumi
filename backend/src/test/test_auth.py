"""Tests for authentication: JWT tokens, password hashing, login flow."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from module.models.user import User
from module.security.jwt import (
    create_access_token,
    decode_token,
    get_password_hash,
    verify_password,
    verify_token,
)

# ---------------------------------------------------------------------------
# JWT Token Creation
# ---------------------------------------------------------------------------


class TestCreateAccessToken:
    def test_creates_valid_token(self):
        """create_access_token returns a decodable JWT with sub claim."""
        token = create_access_token(data={"sub": "testuser"})
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_contains_sub_claim(self):
        """Decoded token contains the 'sub' field."""
        token = create_access_token(data={"sub": "myuser"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "myuser"

    def test_token_contains_exp_claim(self):
        """Decoded token contains 'exp' expiration field."""
        token = create_access_token(data={"sub": "user"})
        payload = decode_token(token)
        assert "exp" in payload

    def test_custom_expiry(self):
        """Custom expires_delta is respected."""
        token = create_access_token(
            data={"sub": "user"}, expires_delta=timedelta(hours=2)
        )
        payload = decode_token(token)
        assert payload is not None


# ---------------------------------------------------------------------------
# Token Decoding
# ---------------------------------------------------------------------------


class TestDecodeToken:
    def test_valid_token(self):
        """decode_token returns payload for valid token."""
        token = create_access_token(data={"sub": "testuser"})
        result = decode_token(token)
        assert result is not None
        assert result["sub"] == "testuser"

    def test_invalid_token(self):
        """decode_token returns None for invalid/garbage token."""
        result = decode_token("not.a.valid.jwt.token")
        assert result is None

    def test_empty_token(self):
        """decode_token returns None for empty string."""
        result = decode_token("")
        assert result is None

    def test_missing_sub_claim(self):
        """decode_token returns None when 'sub' claim is missing."""
        token = create_access_token(data={"other": "data"})
        result = decode_token(token)
        # sub is None so decode_token returns None
        assert result is None


# ---------------------------------------------------------------------------
# Token Verification
# ---------------------------------------------------------------------------


class TestVerifyToken:
    def test_valid_fresh_token(self):
        """verify_token succeeds for a fresh token."""
        token = create_access_token(
            data={"sub": "user"}, expires_delta=timedelta(hours=1)
        )
        result = verify_token(token)
        assert result is not None
        assert result["sub"] == "user"

    def test_expired_token_returns_none(self):
        """verify_token returns None for expired token (caught by decode_token)."""
        token = create_access_token(
            data={"sub": "user"}, expires_delta=timedelta(seconds=-10)
        )
        # PyJWT catches expired tokens during decode, so decode_token
        # returns None, and verify_token propagates that as None
        result = verify_token(token)
        assert result is None

    def test_invalid_token_returns_none(self):
        """verify_token returns None for invalid token (decode fails)."""
        result = verify_token("garbage.token.string")
        assert result is None


# ---------------------------------------------------------------------------
# Password Hashing
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    def test_hash_and_verify_roundtrip(self):
        """get_password_hash then verify_password returns True."""
        password = "my_secure_password"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_wrong_password(self):
        """verify_password with wrong password returns False."""
        hashed = get_password_hash("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_hash_is_not_plaintext(self):
        """Hash is not equal to the plaintext password."""
        password = "my_password"
        hashed = get_password_hash(password)
        assert hashed != password

    def test_different_hashes_for_same_password(self):
        """Bcrypt produces different hashes for the same password (salt)."""
        password = "same_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2
        # Both still verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


# ---------------------------------------------------------------------------
# Long (>72-byte) passwords — passlib silently truncated at 72 bytes, and
# bcrypt 5.x raises ValueError instead. The wrappers must keep passlib's
# truncation semantics so pre-upgrade users with long passwords can still
# log in (and setting a long password doesn't 500).
# ---------------------------------------------------------------------------


class TestLongPasswordTruncation:
    # 30 CJK chars * 3 bytes (UTF-8) = 90 bytes > 72-byte bcrypt limit
    LONG_CJK_PASSWORD = "密码超过七十二字节" * 4

    def test_get_password_hash_over_72_byte_cjk_password_hashes_and_verifies(self):
        """A >72-byte multibyte password hashes without error and verifies."""
        password = self.LONG_CJK_PASSWORD
        assert len(password.encode("utf-8")) > 72
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_pre_upgrade_truncated_hash_full_password_verifies(self):
        """A passlib-era hash (created from the first 72 bytes) still verifies
        against the full long password after the bcrypt migration."""
        import bcrypt

        password = self.LONG_CJK_PASSWORD
        legacy_hash = bcrypt.hashpw(
            password.encode("utf-8")[:72], bcrypt.gensalt()
        ).decode("utf-8")
        assert verify_password(password, legacy_hash) is True

    def test_verify_password_wrong_long_password_fails(self):
        """A long password differing within its first 72 bytes still fails."""
        hashed = get_password_hash(self.LONG_CJK_PASSWORD)
        wrong = "错误密码完全不同的内容" * 4
        assert len(wrong.encode("utf-8")) > 72
        assert verify_password(wrong, hashed) is False

    def test_verify_password_over_72_byte_ascii_password_roundtrip(self):
        """A >72-byte pure-ASCII password also hashes and verifies."""
        password = "a" * 100
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True
        assert verify_password("b" * 100, hashed) is False


# ---------------------------------------------------------------------------
# API Auth Flow (typed principal)
# ---------------------------------------------------------------------------


class TestGetPrincipal:
    @staticmethod
    def _mock_request(authorization=""):
        """Create a mock Request with the given Authorization header."""

        request = MagicMock()
        request.headers = {"authorization": authorization}
        return request

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    async def test_no_cookie_raises_401(self):
        """Authentication raises 401 when no supported credential is present."""
        from fastapi import HTTPException

        from module.security.api import get_principal

        service = MagicMock()
        service.authenticate_api_token = AsyncMock(return_value=None)
        service.authenticate_session = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_principal(
                request=self._mock_request(), token=None, service=service
            )
        assert exc_info.value.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    async def test_invalid_cookie_raises_401(self):
        from fastapi import HTTPException

        from module.security.api import get_principal

        service = MagicMock()
        service.authenticate_api_token = AsyncMock(return_value=None)
        service.authenticate_session = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_principal(
                request=self._mock_request(),
                token="invalid.jwt.token",
                service=service,
            )
        assert exc_info.value.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    async def test_cookie_session_returns_session_principal(self):
        from module.security.api import CredentialKind, get_principal

        user = User(id=1, username="session_user", password="hashed-password")
        service = MagicMock()
        service.authenticate_api_token = AsyncMock(return_value=None)
        service.authenticate_session = AsyncMock(return_value=user)

        principal = await get_principal(
            request=self._mock_request(), token="persisted-session", service=service
        )
        assert principal.kind is CredentialKind.SESSION
        assert principal.user is user
        assert principal.username == "session_user"

    @patch("module.security.api.DEV_AUTH_BYPASS", True)
    async def test_dev_bypass_skips_auth(self):
        from module.security.api import CredentialKind, get_principal

        principal = await get_principal(request=self._mock_request(), token=None)
        assert principal.kind is CredentialKind.DEVELOPMENT
        assert principal.username == "dev_user"

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    async def test_database_api_token_returns_api_principal(self):
        from module.security.api import CredentialKind, get_principal

        user = User(id=1, username="api_user", password="hashed-password")
        service = MagicMock()
        service.authenticate_api_token = AsyncMock(return_value=user)
        service.authenticate_session = AsyncMock(return_value=None)

        principal = await get_principal(
            request=self._mock_request("Bearer valid-api-token"),
            token=None,
            service=service,
        )
        assert principal.kind is CredentialKind.API_TOKEN
        assert principal.username == "api_user"

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    async def test_invalid_authorization_does_not_fall_back_to_cookie(self):
        from fastapi import HTTPException

        from module.security.api import get_principal

        user = User(id=1, username="cookie_user", password="hashed-password")
        service = MagicMock()
        service.authenticate_api_token = AsyncMock(return_value=None)
        service.authenticate_session = AsyncMock(return_value=user)

        with pytest.raises(HTTPException) as exc_info:
            await get_principal(
                request=self._mock_request("Bearer wrong-token"),
                token="valid-cookie-session",
                service=service,
            )
        assert exc_info.value.status_code == 401
        service.authenticate_session.assert_not_awaited()


# ---------------------------------------------------------------------------
# check_login_ip
# ---------------------------------------------------------------------------


class TestCheckLoginIp:
    @staticmethod
    def _make_request(host: str | None):

        request = MagicMock()
        if host is None:
            request.client = None
        else:
            request.client = MagicMock()
            request.client.host = host
        return request

    def test_empty_whitelist_allows_all(self):
        """When login_whitelist is empty, all IPs pass."""
        from module.security.api import check_login_ip

        mock_security = type("S", (), {"login_whitelist": []})()
        mock_settings = type("Settings", (), {"security": mock_security})()

        with patch("module.security.api.settings", mock_settings):
            # Should not raise
            check_login_ip(request=self._make_request("8.8.8.8"))

    def test_allowed_ip_passes(self):
        """IP in whitelist does not raise."""
        from module.security.api import check_login_ip

        mock_security = type("S", (), {"login_whitelist": ["192.168.0.0/16"]})()
        mock_settings = type("Settings", (), {"security": mock_security})()

        with patch("module.security.api.settings", mock_settings):
            check_login_ip(request=self._make_request("192.168.1.100"))

    def test_blocked_ip_raises_403(self):
        """IP outside whitelist raises 403."""
        from fastapi import HTTPException

        from module.security.api import check_login_ip

        mock_security = type("S", (), {"login_whitelist": ["192.168.0.0/16"]})()
        mock_settings = type("Settings", (), {"security": mock_security})()

        with patch("module.security.api.settings", mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                check_login_ip(request=self._make_request("8.8.8.8"))
        assert exc_info.value.status_code == 403

    def test_no_client_raises_403_when_whitelist_set(self):
        """Missing client info raises 403 when whitelist is non-empty."""
        from fastapi import HTTPException

        from module.security.api import check_login_ip

        mock_security = type("S", (), {"login_whitelist": ["192.168.0.0/16"]})()
        mock_settings = type("Settings", (), {"security": mock_security})()

        with patch("module.security.api.settings", mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                check_login_ip(request=self._make_request(None))
        assert exc_info.value.status_code == 403
