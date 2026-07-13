"""Atomicity regressions for authentication application services."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from module.application.auth import AuthenticationError, AuthenticationService
from module.database import Database
from module.models.passkey import Passkey
from module.models.user import UserCreate, UserUpdate


@pytest.mark.asyncio
async def test_password_update_rolls_back_if_session_revocation_fails(db_engine):
    service = AuthenticationService(lambda: Database(db_engine))
    user = await service.create_user(
        UserCreate(username="atomic_user", password="old-password")
    )
    assert user.id is not None
    _user, session_token = await service.login("atomic_user", "old-password")

    with patch(
        "module.database.auth.AuthDatabase.revoke_user_sessions",
        new=AsyncMock(side_effect=RuntimeError("revoke failed")),
    ):
        with pytest.raises(RuntimeError, match="revoke failed"):
            await service.update_user(user.id, UserUpdate(password="new-password"))

    async with Database(db_engine) as db:
        assert await db.user.authenticate_credentials("atomic_user", "old-password")
        assert (
            await db.user.authenticate_credentials("atomic_user", "new-password")
            is None
        )
        assert await db.auth.authenticate_session(session_token)


@pytest.mark.asyncio
async def test_password_update_rolls_back_on_cancellation(db_engine):
    service = AuthenticationService(lambda: Database(db_engine))
    user = await service.create_user(
        UserCreate(username="cancel_user", password="old-password")
    )
    assert user.id is not None
    _user, session_token = await service.login("cancel_user", "old-password")

    with patch(
        "module.database.auth.AuthDatabase.revoke_user_sessions",
        new=AsyncMock(side_effect=asyncio.CancelledError()),
    ):
        with pytest.raises(asyncio.CancelledError):
            await service.update_user(user.id, UserUpdate(password="new-password"))

    async with Database(db_engine) as db:
        assert await db.user.authenticate_credentials("cancel_user", "old-password")
        assert await db.auth.authenticate_session(session_token)


@pytest.mark.asyncio
async def test_password_update_rolls_back_if_final_commit_fails(db_engine):
    service = AuthenticationService(lambda: Database(db_engine))
    user = await service.create_user(
        UserCreate(username="commit_user", password="old-password")
    )
    assert user.id is not None
    _user, session_token = await service.login("commit_user", "old-password")

    with patch(
        "module.database.combine.Database.commit",
        new=AsyncMock(side_effect=RuntimeError("commit failed")),
    ):
        with pytest.raises(RuntimeError, match="commit failed"):
            await service.update_user(user.id, UserUpdate(password="new-password"))

    async with Database(db_engine) as db:
        assert await db.user.authenticate_credentials("commit_user", "old-password")
        assert await db.auth.authenticate_session(session_token)


@pytest.mark.asyncio
async def test_delete_rolls_back_credential_purge_if_user_delete_fails(db_engine):
    service = AuthenticationService(lambda: Database(db_engine))
    target = await service.create_user(
        UserCreate(username="delete_target", password="target-password")
    )
    await service.create_user(
        UserCreate(username="delete_guard", password="guard-password")
    )
    assert target.id is not None

    _user, session_token = await service.login("delete_target", "target-password")
    _stored, api_token = await service.create_api_token_for_user_id(
        target.id, name="automation", scope="api"
    )

    with patch(
        "module.database.user.UserDatabase.delete_user",
        new=AsyncMock(side_effect=RuntimeError("delete failed")),
    ):
        with pytest.raises(RuntimeError, match="delete failed"):
            await service.delete_user(target.id)

    async with Database(db_engine) as db:
        assert await db.user.get_user_by_id(target.id)
        assert await db.auth.authenticate_session(session_token)
        assert await db.auth.authenticate_api_token(api_token, scope="api")


@pytest.mark.asyncio
async def test_api_authentication_survives_audit_write_failure(db_engine):
    service = AuthenticationService(lambda: Database(db_engine))
    user = await service.create_user(
        UserCreate(username="audit_user", password="audit-password")
    )
    assert user.id is not None
    _stored, raw_token = await service.create_api_token_for_user_id(
        user.id, name="automation", scope="api"
    )

    with patch(
        "module.database.auth.AuthDatabase.touch_api_token",
        new=AsyncMock(side_effect=RuntimeError("audit database is busy")),
    ):
        authenticated = await service.authenticate_api_token(raw_token)

    assert authenticated is not None
    assert authenticated.username == "audit_user"


@pytest.mark.asyncio
async def test_account_mutations_keep_identity_when_username_is_reused(db_engine):
    service = AuthenticationService(lambda: Database(db_engine))
    owner = await service.create_user(
        UserCreate(username="mutable_owner", password="owner-password")
    )
    assert owner.id is not None
    await service.update_user(owner.id, UserUpdate(username="renamed_owner"))
    replacement = await service.create_user(
        UserCreate(username="mutable_owner", password="replacement-password")
    )
    assert replacement.id is not None

    updated, _session = await service.update_current_user(
        owner.id, UserUpdate(password="new-owner-password")
    )
    stored, raw_token = await service.create_api_token_for_user_id(
        owner.id, name="owner-token", scope="api"
    )

    assert updated.id == owner.id
    assert stored.user_id == owner.id
    async with Database(db_engine) as db:
        assert await db.user.authenticate_credentials(
            "renamed_owner", "new-owner-password"
        )
        assert await db.user.authenticate_credentials(
            "mutable_owner", "replacement-password"
        )
        authenticated = await db.auth.authenticate_api_token(raw_token, scope="api")
        assert authenticated is not None
        assert authenticated[0].id == owner.id


@pytest.mark.asyncio
async def test_passkey_session_revalidates_credential_after_user_id_reuse(db_engine):
    service = AuthenticationService(lambda: Database(db_engine))
    await service.create_user(
        UserCreate(username="passkey_guard", password="guard-password")
    )
    victim = await service.create_user(
        UserCreate(username="passkey_victim", password="victim-password")
    )
    assert victim.id is not None
    credential_id = "stable-passkey-credential"
    async with Database(db_engine) as db:
        db.add(
            Passkey(
                user_id=victim.id,
                name="Security key",
                credential_id=credential_id,
                public_key="encoded-public-key",
            )
        )
        await db.commit()

    session = await service.issue_session_for_verified_passkey(victim.id, credential_id)
    async with Database(db_engine) as db:
        authenticated = await db.auth.authenticate_session(session)
        assert authenticated is not None
        assert authenticated.id == victim.id

    await service.delete_user(victim.id)
    replacement = await service.create_user(
        UserCreate(username="passkey_replacement", password="replacement-password")
    )
    assert replacement.id == victim.id  # SQLite reuses the deleted maximum ROWID.

    with pytest.raises(AuthenticationError, match="not available"):
        await service.issue_session_for_verified_passkey(replacement.id, credential_id)
