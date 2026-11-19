from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(
        default="admin",
        min_length=4,
        max_length=20,
        regex=r"^[a-zA-Z0-9_]+$",
        unique=True,
        index=True,
    )
    password: str = Field(default="", min_length=8)
    enabled: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserUpdate(SQLModel):
    username: str | None = Field(
        default=None, min_length=4, max_length=20, regex=r"^[a-zA-Z0-9_]+$"
    )
    password: str | None = Field(default=None, min_length=8)
    enabled: bool | None = None


class UserCredentialsUpdate(BaseModel):
    """Credential fields a signed-in user may change on their own account."""

    model_config = ConfigDict(extra="forbid")

    username: str | None = Field(
        default=None, min_length=4, max_length=20, regex=r"^[a-zA-Z0-9_]+$"
    )
    password: str | None = Field(default=None, min_length=8)


class UserCreate(SQLModel):
    username: str = Field(min_length=4, max_length=20, regex=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8)


class UserPublic(SQLModel):
    id: int
    username: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class AuthenticationSuccess(SQLModel):
    """Non-secret response shared by every browser-session issuing endpoint."""

    authenticated: Literal[True] = True
