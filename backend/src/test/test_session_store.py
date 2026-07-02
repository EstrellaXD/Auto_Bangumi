"""Tests for SessionStore expiry and the constant-time bearer-token path."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from module.conf import settings
from module.security.api import SessionStore, get_current_user

# ---------------------------------------------------------------------------
# SessionStore
# ---------------------------------------------------------------------------


class TestSessionStore:
    def test_add_then_present(self):
        store = SessionStore()
        store.add("alice")
        assert "alice" in store

    def test_absent_user_not_present(self):
        store = SessionStore()
        assert "nobody" not in store

    def test_remove(self):
        store = SessionStore()
        store.add("alice")
        store.remove("alice")
        assert "alice" not in store

    def test_remove_missing_is_noop(self):
        store = SessionStore()
        store.remove("ghost")  # must not raise
        assert len(store) == 0

    def test_clear(self):
        store = SessionStore()
        store.add("a")
        store.add("b")
        store.clear()
        assert len(store) == 0

    def test_expired_entry_is_evicted_on_access(self):
        """An entry older than the lifetime is treated as absent and dropped."""
        store = SessionStore(lifetime=timedelta(hours=1))
        store.add("alice")
        # Backdate the recorded session beyond the lifetime.
        store._sessions["alice"] = datetime.now() - timedelta(hours=2)
        assert "alice" not in store
        # Lazily evicted, so the backing dict no longer holds it.
        assert len(store) == 0

    def test_fresh_entry_within_lifetime_is_present(self):
        store = SessionStore(lifetime=timedelta(hours=1))
        store.add("alice")
        store._sessions["alice"] = datetime.now() - timedelta(minutes=30)
        assert "alice" in store


# ---------------------------------------------------------------------------
# Bearer-token path uses constant-time comparison
# ---------------------------------------------------------------------------


def _mock_request(authorization: str = "") -> MagicMock:
    request = MagicMock()
    request.headers = {"authorization": authorization}
    return request


class TestBearerTokenCompareDigest:
    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    async def test_matching_token_authenticates(self):
        """A configured bearer token authenticates via compare_digest."""
        with patch.object(settings.security, "login_tokens", ["secret-token"]):
            result = await get_current_user(
                request=_mock_request("Bearer secret-token"), token=None
            )
        assert result == "api_token_user"

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    async def test_wrong_token_rejected(self):
        """A non-matching bearer token falls through to 401 (no cookie)."""
        with patch.object(settings.security, "login_tokens", ["secret-token"]):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(
                    request=_mock_request("Bearer wrong-token"), token=None
                )
        assert exc_info.value.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    async def test_no_tokens_configured_rejected(self):
        """With no configured tokens, a bearer header cannot authenticate."""
        with patch.object(settings.security, "login_tokens", []):
            with pytest.raises(HTTPException):
                await get_current_user(
                    request=_mock_request("Bearer anything"), token=None
                )
