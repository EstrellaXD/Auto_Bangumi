"""Async persistence adapter for sessions and bearer tokens."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, delete, select

from module.models.auth import ApiToken, AuthSession
from module.models.passkey import Passkey
from module.models.user import User

DEFAULT_SESSION_TTL = timedelta(days=1)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _legacy_token_fingerprint(token_hash: str) -> str:
    """Return display metadata that cannot reveal any raw legacy token text."""
    return f"legacy_{token_hash[:8]}"


class AuthDatabase:
    """Repository that stores only SHA-256 token digests."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(
        self,
        user_id: int,
        *,
        now: datetime | None = None,
        ttl: timedelta = DEFAULT_SESSION_TTL,
        commit: bool = True,
    ) -> str:
        issued_at = _utc(now or datetime.now(timezone.utc))
        raw_token = secrets.token_urlsafe(48)
        self.session.add(
            AuthSession(
                user_id=user_id,
                token_hash=_hash_token(raw_token),
                created_at=issued_at,
                last_seen_at=issued_at,
                expires_at=issued_at + ttl,
            )
        )
        if commit:
            await self.session.commit()
        else:
            await self.session.flush()
        return raw_token

    async def authenticate_session(
        self, raw_token: str, *, now: datetime | None = None
    ) -> User | None:
        if not raw_token:
            return None
        current = _utc(now or datetime.now(timezone.utc))
        result = await self.session.execute(
            select(AuthSession).where(
                AuthSession.token_hash == _hash_token(raw_token),
                col(AuthSession.revoked_at).is_(None),
            )
        )
        auth_session = result.scalars().first()
        if auth_session is None or _utc(auth_session.expires_at) <= current:
            return None
        user = await self.session.get(User, auth_session.user_id)
        if user is None or not user.enabled:
            return None
        return user

    async def refresh_session(
        self,
        raw_token: str,
        *,
        now: datetime | None = None,
        ttl: timedelta = DEFAULT_SESSION_TTL,
    ) -> User | None:
        current = _utc(now or datetime.now(timezone.utc))
        result = await self.session.execute(
            update(AuthSession)
            .where(
                col(AuthSession.token_hash) == _hash_token(raw_token),
                col(AuthSession.revoked_at).is_(None),
                col(AuthSession.expires_at) > current,
            )
            .values(last_seen_at=current, expires_at=current + ttl)
            .returning(col(AuthSession.user_id))
        )
        user_id = result.scalar_one_or_none()
        if user_id is None:
            await self.session.rollback()
            return None
        user = await self.session.get(User, user_id)
        if user is None or not user.enabled:
            await self.session.rollback()
            return None
        await self.session.commit()
        return user

    async def revoke_session(
        self, raw_token: str, *, now: datetime | None = None
    ) -> bool:
        if not raw_token:
            return False
        current = _utc(now or datetime.now(timezone.utc))
        result = await self.session.execute(
            update(AuthSession)
            .where(
                col(AuthSession.token_hash) == _hash_token(raw_token),
                col(AuthSession.revoked_at).is_(None),
            )
            .values(revoked_at=current)
        )
        await self.session.commit()
        return bool(getattr(result, "rowcount", 0))

    async def revoke_user_sessions(
        self,
        user_id: int,
        *,
        now: datetime | None = None,
        commit: bool = True,
    ) -> int:
        current = _utc(now or datetime.now(timezone.utc))
        result = await self.session.execute(
            update(AuthSession)
            .where(
                col(AuthSession.user_id) == user_id,
                col(AuthSession.revoked_at).is_(None),
            )
            .values(revoked_at=current)
        )
        if commit:
            await self.session.commit()
        else:
            await self.session.flush()
        return int(getattr(result, "rowcount", 0) or 0)

    async def create_api_token(
        self,
        user_id: int,
        *,
        name: str,
        scope: str,
        now: datetime | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[ApiToken, str]:
        if scope not in {"api", "mcp"}:
            raise ValueError("Unsupported API token scope")
        issued_at = _utc(now or datetime.now(timezone.utc))
        raw_token = f"ab_{scope}_{secrets.token_urlsafe(36)}"
        token = ApiToken(
            user_id=user_id,
            name=name,
            scope=scope,
            token_hash=_hash_token(raw_token),
            prefix=raw_token[:12],
            created_at=issued_at,
            expires_at=_utc(expires_at) if expires_at else None,
        )
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token, raw_token

    async def import_api_token(
        self,
        user_id: int,
        raw_token: str,
        *,
        name: str,
        scope: str,
        now: datetime | None = None,
    ) -> ApiToken:
        if scope not in {"api", "mcp"}:
            raise ValueError("Unsupported API token scope")
        token_hash = _hash_token(raw_token)
        await self.session.execute(
            sqlite_insert(ApiToken)
            .values(
                user_id=user_id,
                name=name,
                scope=scope,
                token_hash=token_hash,
                prefix=_legacy_token_fingerprint(token_hash),
                created_at=_utc(now or datetime.now(timezone.utc)),
            )
            .on_conflict_do_nothing(index_elements=["token_hash", "scope"])
        )
        result = await self.session.execute(
            select(ApiToken).where(
                ApiToken.token_hash == token_hash,
                ApiToken.scope == scope,
            )
        )
        token = result.scalar_one()
        await self.session.commit()
        return token

    async def authenticate_api_token(
        self,
        raw_token: str,
        *,
        scope: str,
        now: datetime | None = None,
    ) -> tuple[User, int] | None:
        if not raw_token:
            return None
        current = _utc(now or datetime.now(timezone.utc))
        result = await self.session.execute(
            select(ApiToken).where(
                ApiToken.token_hash == _hash_token(raw_token),
                ApiToken.scope == scope,
                col(ApiToken.revoked_at).is_(None),
            )
        )
        token = result.scalars().first()
        if token is None:
            return None
        if token.expires_at is not None and _utc(token.expires_at) <= current:
            return None
        user = await self.session.get(User, token.user_id)
        if user is None or not user.enabled:
            return None
        if token.id is None:
            raise RuntimeError("Persisted API token has no primary key")
        return user, token.id

    async def touch_api_token(
        self, token_id: int, *, now: datetime | None = None
    ) -> None:
        """Update best-effort usage metadata with a direct write transaction."""
        current = _utc(now or datetime.now(timezone.utc))
        await self.session.execute(
            update(ApiToken)
            .where(col(ApiToken.id) == token_id)
            .values(last_used_at=current)
        )
        await self.session.commit()

    async def revoke_api_token(
        self, token_id: int, *, now: datetime | None = None
    ) -> bool:
        result = await self.session.execute(
            update(ApiToken)
            .where(
                col(ApiToken.id) == token_id,
                col(ApiToken.revoked_at).is_(None),
            )
            .values(revoked_at=_utc(now or datetime.now(timezone.utc)))
        )
        await self.session.commit()
        return bool(getattr(result, "rowcount", 0))

    async def passkey_belongs_to_user(self, user_id: int, credential_id: str) -> bool:
        result = await self.session.execute(
            select(Passkey.id).where(
                col(Passkey.user_id) == user_id,
                col(Passkey.credential_id) == credential_id,
            )
        )
        return result.first() is not None

    async def list_api_tokens(self) -> list[ApiToken]:
        result = await self.session.execute(
            select(ApiToken).order_by(col(ApiToken.created_at).desc())
        )
        return list(result.scalars().all())

    async def purge_user_credentials(
        self, user_id: int, *, commit: bool = True
    ) -> None:
        """Remove credentials before deleting their owning user."""
        await self.session.execute(
            delete(AuthSession).where(col(AuthSession.user_id) == user_id)
        )
        await self.session.execute(
            delete(ApiToken).where(col(ApiToken.user_id) == user_id)
        )
        await self.session.execute(
            delete(Passkey).where(col(Passkey.user_id) == user_id)
        )
        if commit:
            await self.session.commit()
        else:
            await self.session.flush()
