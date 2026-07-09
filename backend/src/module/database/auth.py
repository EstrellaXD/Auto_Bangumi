"""Async persistence adapter for sessions and bearer tokens."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

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
        await self.session.commit()
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
                AuthSession.revoked_at.is_(None),
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
        user = await self.authenticate_session(raw_token, now=current)
        if user is None:
            return None
        result = await self.session.execute(
            select(AuthSession).where(AuthSession.token_hash == _hash_token(raw_token))
        )
        auth_session = result.scalar_one()
        auth_session.last_seen_at = current
        auth_session.expires_at = current + ttl
        self.session.add(auth_session)
        await self.session.commit()
        return user

    async def revoke_session(
        self, raw_token: str, *, now: datetime | None = None
    ) -> bool:
        if not raw_token:
            return False
        result = await self.session.execute(
            select(AuthSession).where(
                AuthSession.token_hash == _hash_token(raw_token),
                AuthSession.revoked_at.is_(None),
            )
        )
        auth_session = result.scalars().first()
        if auth_session is None:
            return False
        auth_session.revoked_at = _utc(now or datetime.now(timezone.utc))
        self.session.add(auth_session)
        await self.session.commit()
        return True

    async def revoke_user_sessions(
        self, user_id: int, *, now: datetime | None = None
    ) -> int:
        current = _utc(now or datetime.now(timezone.utc))
        result = await self.session.execute(
            select(AuthSession).where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
        )
        sessions = list(result.scalars().all())
        for auth_session in sessions:
            auth_session.revoked_at = current
            self.session.add(auth_session)
        await self.session.commit()
        return len(sessions)

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
        token_hash = _hash_token(raw_token)
        result = await self.session.execute(
            select(ApiToken).where(ApiToken.token_hash == token_hash)
        )
        existing = result.scalars().first()
        if existing is not None:
            return existing
        if scope not in {"api", "mcp"}:
            raise ValueError("Unsupported API token scope")
        token = ApiToken(
            user_id=user_id,
            name=name,
            scope=scope,
            token_hash=token_hash,
            prefix=raw_token[:12],
            created_at=_utc(now or datetime.now(timezone.utc)),
        )
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token

    async def authenticate_api_token(
        self,
        raw_token: str,
        *,
        scope: str,
        now: datetime | None = None,
    ) -> User | None:
        if not raw_token:
            return None
        current = _utc(now or datetime.now(timezone.utc))
        result = await self.session.execute(
            select(ApiToken).where(
                ApiToken.token_hash == _hash_token(raw_token),
                ApiToken.scope == scope,
                ApiToken.revoked_at.is_(None),
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
        token.last_used_at = current
        self.session.add(token)
        await self.session.commit()
        return user

    async def revoke_api_token(
        self, token_id: int, *, now: datetime | None = None
    ) -> bool:
        token = await self.session.get(ApiToken, token_id)
        if token is None or token.revoked_at is not None:
            return False
        token.revoked_at = _utc(now or datetime.now(timezone.utc))
        self.session.add(token)
        await self.session.commit()
        return True

    async def list_api_tokens(self) -> list[ApiToken]:
        result = await self.session.execute(
            select(ApiToken).order_by(col(ApiToken.created_at).desc())
        )
        return list(result.scalars().all())

    async def purge_user_credentials(self, user_id: int) -> None:
        """Remove credentials before deleting their owning user."""
        await self.session.execute(
            delete(AuthSession).where(AuthSession.user_id == user_id)
        )
        await self.session.execute(delete(ApiToken).where(ApiToken.user_id == user_id))
        await self.session.execute(delete(Passkey).where(Passkey.user_id == user_id))
        await self.session.commit()
