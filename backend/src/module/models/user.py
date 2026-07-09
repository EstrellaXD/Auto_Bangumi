from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(
        "admin",
        min_length=4,
        max_length=20,
        regex=r"^[a-zA-Z0-9_]+$",
        unique=True,
        index=True,
    )
    password: str = Field("", min_length=8)
    enabled: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserUpdate(SQLModel):
    username: Optional[str] = Field(
        None, min_length=4, max_length=20, regex=r"^[a-zA-Z0-9_]+$"
    )
    password: Optional[str] = Field(None, min_length=8)
    enabled: Optional[bool] = None


class UserCreate(SQLModel):
    username: str = Field(min_length=4, max_length=20, regex=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8)


class UserPublic(SQLModel):
    id: int
    username: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class UserLogin(SQLModel):
    username: str
    password: str = Field(..., min_length=8)


class Token(BaseModel):
    token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None
