"""Tests for the legacy SessionStore compatibility helper."""

from datetime import datetime, timedelta

from module.security.api import SessionStore

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
