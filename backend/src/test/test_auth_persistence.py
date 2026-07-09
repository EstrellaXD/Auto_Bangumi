"""Persistent multi-user authentication behavior."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import select

from module.application.auth import AuthenticationService, ConflictError
from module.database import Database
from module.models.auth import ApiToken, AuthSession
from module.models.config import Config
from module.models.user import UserCreate, UserUpdate
from module.update.auth import migrate_legacy_auth_tokens


@pytest.mark.asyncio
async def test_sessions_persist_and_are_isolated_between_users(db_engine):
    now = datetime.now(timezone.utc)
    async with Database(db_engine) as db:
        alice = await db.user.create_user("alice_user", "alice-password")
        bob = await db.user.create_user("bob_user", "bob-password")
        alice_token = await db.auth.create_session(alice.id, now=now)
        bob_token = await db.auth.create_session(bob.id, now=now)

    async with Database(db_engine) as reopened:
        alice_user = await reopened.auth.authenticate_session(alice_token, now=now)
        bob_user = await reopened.auth.authenticate_session(bob_token, now=now)
        assert alice_user and alice_user.username == "alice_user"
        assert bob_user and bob_user.username == "bob_user"

        await reopened.auth.revoke_session(alice_token)
        assert await reopened.auth.authenticate_session(alice_token, now=now) is None
        assert await reopened.auth.authenticate_session(bob_token, now=now)


@pytest.mark.asyncio
async def test_session_tokens_are_hashed_and_expire(db_engine):
    now = datetime.now(timezone.utc)
    async with Database(db_engine) as db:
        user = await db.user.create_user("session_user", "session-password")
        raw_token = await db.auth.create_session(
            user.id, now=now, ttl=timedelta(minutes=5)
        )
        result = await db.session.execute(select(AuthSession))
        stored = result.scalar_one()
        assert stored.token_hash != raw_token
        assert raw_token not in stored.token_hash
        assert await db.auth.authenticate_session(raw_token, now=now)
        assert (
            await db.auth.authenticate_session(
                raw_token, now=now + timedelta(minutes=6)
            )
            is None
        )


@pytest.mark.asyncio
async def test_last_enabled_user_invariants_and_session_revocation(db_engine):
    service = AuthenticationService(lambda: Database(db_engine))
    only = await service.create_user(
        UserCreate(username="only_user", password="only-password")
    )
    assert only.id is not None

    with pytest.raises(ConflictError, match="last enabled user"):
        await service.update_user(only.id, UserUpdate(enabled=False))
    with pytest.raises(ConflictError, match="last enabled user"):
        await service.delete_user(only.id)

    second = await service.create_user(
        UserCreate(username="second_user", password="second-password")
    )
    assert second.id is not None
    _user, token = await service.login("second_user", "second-password")
    await service.update_user(second.id, UserUpdate(enabled=False))
    assert await service.authenticate_session(token) is None


@pytest.mark.asyncio
async def test_api_tokens_are_hashed_scoped_and_revocable(db_engine):
    now = datetime.now(timezone.utc)
    async with Database(db_engine) as db:
        user = await db.user.create_user("token_user", "token-password")
        stored, raw_token = await db.auth.create_api_token(
            user.id, name="automation", scope="api", now=now
        )
        result = await db.session.execute(select(ApiToken))
        persisted = result.scalar_one()
        assert persisted.token_hash != raw_token
        assert persisted.prefix == raw_token[:12]
        assert await db.auth.authenticate_api_token(raw_token, scope="api", now=now)
        assert (
            await db.auth.authenticate_api_token(raw_token, scope="mcp", now=now)
            is None
        )
        await db.auth.revoke_api_token(stored.id)
        assert (
            await db.auth.authenticate_api_token(raw_token, scope="api", now=now)
            is None
        )


@pytest.mark.asyncio
async def test_legacy_config_tokens_are_imported_once(db_engine):
    class RuntimeSettings(Config):
        saved: bool = False

        def save(self, config_dict=None):
            self.saved = True

    runtime_settings = RuntimeSettings()
    runtime_settings.security.login_tokens = ["legacy-login-token"]
    runtime_settings.security.mcp_tokens = ["legacy-mcp-token"]
    async with Database(db_engine) as db:
        await db.user.create_user("import_user", "import-password")

    imported = await migrate_legacy_auth_tokens(
        database_factory=lambda: Database(db_engine),
        runtime_settings=runtime_settings,
    )

    assert imported == 2
    assert runtime_settings.saved is True
    assert runtime_settings.security.login_tokens == []
    assert runtime_settings.security.mcp_tokens == []
    async with Database(db_engine) as db:
        api_user = await db.auth.authenticate_api_token(
            "legacy-login-token", scope="api"
        )
        mcp_user = await db.auth.authenticate_api_token("legacy-mcp-token", scope="mcp")
        assert api_user and api_user.username == "import_user"
        assert mcp_user and mcp_user.username == "import_user"
