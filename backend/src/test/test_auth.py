"""Tests for authentication: JWT tokens, password hashing, login flow."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from jose import JWTError

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
        # python-jose catches expired tokens during decode, so decode_token
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
# API Auth Flow (get_current_user)
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    @staticmethod
    def _mock_request(authorization=""):
        """Create a mock Request with the given Authorization header."""
        from unittest.mock import MagicMock

        request = MagicMock()
        request.headers = {"authorization": authorization}
        return request

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    async def test_no_cookie_raises_401(self):
        """get_current_user raises 401 when no token cookie."""
        from fastapi import HTTPException

        from module.security.api import get_current_user

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request=self._mock_request(), token=None)
        assert exc_info.value.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    async def test_invalid_token_raises_401(self):
        """get_current_user raises 401 for invalid token."""
        from fastapi import HTTPException

        from module.security.api import get_current_user

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request=self._mock_request(), token="invalid.jwt.token")
        assert exc_info.value.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    async def test_valid_token_user_not_active(self):
        """get_current_user raises 401 when user not in active_user list."""
        from fastapi import HTTPException

        from module.security.api import active_user, get_current_user

        token = create_access_token(
            data={"sub": "ghost_user"}, expires_delta=timedelta(hours=1)
        )
        active_user.clear()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request=self._mock_request(), token=token)
        assert exc_info.value.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    async def test_valid_token_active_user_succeeds(self):
        """get_current_user returns username for valid token + active user."""
        from module.security.api import active_user, get_current_user

        token = create_access_token(
            data={"sub": "active_user"}, expires_delta=timedelta(hours=1)
        )
        active_user.clear()
        active_user.add("active_user")

        result = await get_current_user(request=self._mock_request(), token=token)
        assert result == "active_user"

        # Cleanup
        active_user.clear()

    @patch("module.security.api.DEV_AUTH_BYPASS", True)
    async def test_dev_bypass_skips_auth(self):
        """When DEV_AUTH_BYPASS is True, get_current_user returns 'dev_user' unconditionally."""
        from module.security.api import get_current_user

        result = await get_current_user(request=self._mock_request(), token=None)
        assert result == "dev_user"

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    async def test_bearer_token_bypass_valid(self):
        """A valid login_token in Authorization header returns 'api_token_user'."""
        from module.security.api import get_current_user

        mock_request = self._mock_request(authorization="Bearer valid-api-token")
        mock_security = type("S", (), {"login_tokens": ["valid-api-token"]})()
        mock_settings = type("Settings", (), {"security": mock_security})()

        with patch("module.security.api.settings", mock_settings):
            result = await get_current_user(request=mock_request, token=None)
        assert result == "api_token_user"

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    async def test_bearer_token_bypass_invalid(self):
        """An invalid login_token still falls through to cookie check."""
        from fastapi import HTTPException

        from module.security.api import get_current_user

        mock_request = self._mock_request(authorization="Bearer wrong-token")
        mock_security = type("S", (), {"login_tokens": ["correct-token"]})()
        mock_settings = type("Settings", (), {"security": mock_security})()

        with patch("module.security.api.settings", mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(request=mock_request, token=None)
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# check_login_ip
# ---------------------------------------------------------------------------


class TestCheckLoginIp:
    @staticmethod
    def _make_request(host: str | None):
        from unittest.mock import MagicMock

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
