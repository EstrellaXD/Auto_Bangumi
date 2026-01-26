"""Tests for authentication: JWT tokens, password hashing, login flow."""

import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock

from jose import JWTError

from module.security.jwt import (
    create_access_token,
    decode_token,
    verify_token,
    verify_password,
    get_password_hash,
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
    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    async def test_no_cookie_raises_401(self):
        """get_current_user raises 401 when no token cookie."""
        from module.security.api import get_current_user
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=None)
        assert exc_info.value.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    async def test_invalid_token_raises_401(self):
        """get_current_user raises 401 for invalid token."""
        from module.security.api import get_current_user
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="invalid.jwt.token")
        assert exc_info.value.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    async def test_valid_token_user_not_active(self):
        """get_current_user raises 401 when user not in active_user list."""
        from module.security.api import get_current_user, active_user
        from fastapi import HTTPException

        token = create_access_token(
            data={"sub": "ghost_user"}, expires_delta=timedelta(hours=1)
        )
        active_user.clear()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token)
        assert exc_info.value.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    async def test_valid_token_active_user_succeeds(self):
        """get_current_user returns username for valid token + active user."""
        from module.security.api import get_current_user, active_user

        token = create_access_token(
            data={"sub": "active_user"}, expires_delta=timedelta(hours=1)
        )
        active_user.clear()
        active_user.append("active_user")

        result = await get_current_user(token=token)
        assert result == "active_user"

        # Cleanup
        active_user.clear()
