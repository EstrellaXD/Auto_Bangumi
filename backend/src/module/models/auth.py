"""Persistent authentication models."""

from datetime import datetime, timezone
from typing import Literal

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuthSession(SQLModel, table=True):
    """Revocable browser or bearer session stored as a token hash."""

    __tablename__ = "auth_session"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    token_hash: str = Field(unique=True, index=True, max_length=64)
    created_at: datetime = Field(default_factory=utc_now)
    last_seen_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime = Field(index=True)
    revoked_at: datetime | None = Field(default=None, index=True)


class ApiToken(SQLModel, table=True):
    """Hashed API or MCP bearer token."""

    __tablename__ = "api_token"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str = Field(min_length=1, max_length=64)
    scope: str = Field(index=True, max_length=8)
    token_hash: str = Field(unique=True, index=True, max_length=64)
    prefix: str = Field(max_length=16)
    created_at: datetime = Field(default_factory=utc_now)
    last_used_at: datetime | None = None
    expires_at: datetime | None = Field(default=None, index=True)
    revoked_at: datetime | None = Field(default=None, index=True)


class ApiTokenCreate(SQLModel):
    name: str = Field(min_length=1, max_length=64)
    scope: Literal["api", "mcp"] = "api"
    expires_at: datetime | None = None


class ApiTokenPublic(SQLModel):
    id: int
    user_id: int
    name: str
    scope: Literal["api", "mcp"]
    prefix: str
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None


class ApiTokenCreated(ApiTokenPublic):
    token: str
