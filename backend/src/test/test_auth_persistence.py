"""Persistent multi-user authentication behavior."""

import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel, func, select

from module.application.auth import AuthenticationService, ConflictError
from module.database import Database
from module.database.user import UserDatabase
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
        matched = await db.auth.authenticate_api_token(raw_token, scope="api", now=now)
        assert matched is not None
        matched_user, matched_token_id = matched
        assert matched_user.username == "token_user"
        assert matched_token_id == stored.id
        assert persisted.last_used_at is None
        assert (
            await db.auth.authenticate_api_token(raw_token, scope="mcp", now=now)
            is None
        )
        await db.auth.touch_api_token(matched_token_id, now=now + timedelta(seconds=1))
        await db.session.refresh(persisted)
        assert persisted.last_used_at is not None
        await db.auth.revoke_api_token(stored.id)
        assert (
            await db.auth.authenticate_api_token(raw_token, scope="api", now=now)
            is None
        )


@pytest.mark.asyncio
async def test_legacy_config_tokens_preserve_scopes_without_leaking_prefix(db_engine):
    class RuntimeSettings(Config):
        saved: bool = False

        def save(self, config_dict=None):
            self.saved = True

    runtime_settings = RuntimeSettings()
    short_token = "tiny"
    shared_token = "shared-api-and-mcp-secret"
    runtime_settings.security.login_tokens = [short_token, shared_token]
    runtime_settings.security.mcp_tokens = [shared_token]
    async with Database(db_engine) as db:
        await db.user.create_user("import_user", "import-password")

    imported = await migrate_legacy_auth_tokens(
        database_factory=lambda: Database(db_engine),
        runtime_settings=runtime_settings,
    )

    assert imported == 3
    assert runtime_settings.saved is True
    assert runtime_settings.security.login_tokens == []
    assert runtime_settings.security.mcp_tokens == []
    async with Database(db_engine) as db:
        result = await db.session.execute(select(ApiToken))
        stored_tokens = list(result.scalars().all())
        assert len(stored_tokens) == 3
        assert {(token.token_hash, token.scope) for token in stored_tokens} == {
            (hashlib.sha256(short_token.encode()).hexdigest(), "api"),
            (hashlib.sha256(shared_token.encode()).hexdigest(), "api"),
            (hashlib.sha256(shared_token.encode()).hexdigest(), "mcp"),
        }
        for token in stored_tokens:
            assert token.prefix == f"legacy_{token.token_hash[:8]}"
            assert short_token not in token.prefix
            assert shared_token not in token.prefix

        api_match = await db.auth.authenticate_api_token(short_token, scope="api")
        shared_api_match = await db.auth.authenticate_api_token(
            shared_token, scope="api"
        )
        mcp_match = await db.auth.authenticate_api_token(shared_token, scope="mcp")
        assert api_match and api_match[0].username == "import_user"
        assert shared_api_match and shared_api_match[0].username == "import_user"
        assert mcp_match and mcp_match[0].username == "import_user"
        assert shared_api_match[1] != mcp_match[1]

        touched_at = datetime.now(timezone.utc)
        await db.auth.touch_api_token(shared_api_match[1], now=touched_at)
        result = await db.session.execute(
            select(ApiToken).where(
                ApiToken.token_hash == hashlib.sha256(shared_token.encode()).hexdigest()
            )
        )
        by_scope = {token.scope: token for token in result.scalars().all()}
        assert by_scope["api"].last_used_at is not None
        assert by_scope["mcp"].last_used_at is None


@pytest.mark.asyncio
async def test_concurrent_legacy_token_import_is_idempotent(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'concurrent-import.db'}",
        connect_args={"timeout": 5},
        poolclass=NullPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    try:
        async with Database(engine) as db:
            user = await db.user.create_user("import_owner", "import-password")
            assert user.id is not None
            user_id = user.id

        async def import_once():
            async with Database(engine) as db:
                return await db.auth.import_api_token(
                    user_id,
                    "same-concurrent-secret",
                    name="Imported API token",
                    scope="api",
                )

        first, second = await asyncio.gather(import_once(), import_once())
        assert first.id == second.id

        async with Database(engine) as db:
            result = await db.session.execute(
                select(func.count())
                .select_from(ApiToken)
                .where(
                    ApiToken.token_hash
                    == hashlib.sha256(b"same-concurrent-secret").hexdigest(),
                    ApiToken.scope == "api",
                )
            )
            assert result.scalar_one() == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_commit_false_auth_mutations_flush_and_rollback_together(db_engine):
    async with Database(db_engine) as db:
        user = await db.user.create_user("rollback_user", "old-password")
        assert user.id is not None
        user_id = user.id
        original_session = await db.auth.create_session(user_id)

    async with Database(db_engine) as db:
        await db.begin_write()
        await db.user.update_user_by_id(
            user_id,
            UserUpdate(password="new-password"),
            commit=False,
        )
        await db.auth.revoke_user_sessions(user_id, commit=False)
        replacement_session = await db.auth.create_session(user_id, commit=False)

        assert await db.user.authenticate_credentials("rollback_user", "new-password")
        assert await db.auth.authenticate_session(original_session) is None
        assert await db.auth.authenticate_session(replacement_session)
        await db.rollback()

    async with Database(db_engine) as db:
        assert await db.user.authenticate_credentials("rollback_user", "old-password")
        assert (
            await db.user.authenticate_credentials("rollback_user", "new-password")
            is None
        )
        assert await db.auth.authenticate_session(original_session)
        assert await db.auth.authenticate_session(replacement_session) is None


@pytest.mark.asyncio
async def test_commit_false_purge_and_delete_can_be_rolled_back(db_engine):
    async with Database(db_engine) as db:
        target = await db.user.create_user("purge_target", "target-password")
        await db.user.create_user("purge_guard", "guard-password")
        assert target.id is not None
        target_id = target.id
        session_token = await db.auth.create_session(target_id)
        _stored, api_token = await db.auth.create_api_token(
            target_id, name="automation", scope="api"
        )

    async with Database(db_engine) as db:
        await db.begin_write()
        await db.auth.purge_user_credentials(target_id, commit=False)
        assert await db.user.delete_user(target_id, commit=False)
        await db.rollback()

    async with Database(db_engine) as db:
        assert await db.user.get_user_by_id(target_id)
        assert await db.auth.authenticate_session(session_token)
        assert await db.auth.authenticate_api_token(api_token, scope="api")


@pytest.mark.asyncio
async def test_begin_immediate_serializes_concurrent_last_user_updates(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'last-user.db'}",
        connect_args={"timeout": 5},
        poolclass=NullPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    try:
        service = AuthenticationService(lambda: Database(engine))
        first = await service.create_user(
            UserCreate(username="first_enabled", password="first-password")
        )
        second = await service.create_user(
            UserCreate(username="second_enabled", password="second-password")
        )
        assert first.id is not None
        assert second.id is not None

        results = await asyncio.gather(
            service.update_user(first.id, UserUpdate(enabled=False)),
            service.update_user(second.id, UserUpdate(enabled=False)),
            return_exceptions=True,
        )

        assert sum(isinstance(result, ConflictError) for result in results) == 1
        async with Database(engine) as db:
            assert await db.user.enabled_count() == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_login_prevents_wal_read_to_write_snapshot_upgrade(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'login-wal.db'}",
        connect_args={"timeout": 2},
        poolclass=NullPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with engine.connect() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.commit()

    service = AuthenticationService(lambda: Database(engine))
    user = await service.create_user(
        UserCreate(username="wal_login", password="login-password")
    )
    assert user.id is not None
    read_complete = asyncio.Event()
    release_login = asyncio.Event()
    writer_ready = asyncio.Event()
    original_authenticate = UserDatabase.authenticate_credentials

    async def pause_after_read(repository, username, password):
        authenticated = await original_authenticate(repository, username, password)
        read_complete.set()
        await release_login.wait()
        return authenticated

    async def competing_writer():
        async with engine.begin() as conn:
            writer_ready.set()
            await conn.execute(
                text("UPDATE user SET updated_at = CURRENT_TIMESTAMP WHERE id = :id"),
                {"id": user.id},
            )

    try:
        with patch.object(
            UserDatabase, "authenticate_credentials", new=pause_after_read
        ):
            login_task = asyncio.create_task(
                service.login("wal_login", "login-password")
            )
            await asyncio.wait_for(read_complete.wait(), timeout=2)
            writer_task = asyncio.create_task(competing_writer())
            await asyncio.wait_for(writer_ready.wait(), timeout=2)

            writer_finished_before_login = False
            try:
                await asyncio.wait_for(asyncio.shield(writer_task), timeout=0.2)
                writer_finished_before_login = True
            except asyncio.TimeoutError:
                pass
            finally:
                release_login.set()

            _authenticated, session_token = await asyncio.wait_for(
                login_task, timeout=2
            )
            await asyncio.wait_for(writer_task, timeout=2)

        assert writer_finished_before_login is False
        assert await service.authenticate_session(session_token)
    finally:
        await engine.dispose()
