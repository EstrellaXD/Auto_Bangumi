from pydantic import BaseModel, Field
from typing import Optional
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    username: str = Field(
        "admin", min_length=4, max_length=20, regex=r"^[a-zA-Z0-9_]+$"
    )
    password: str = Field("adminadmin", min_length=8)


class UserUpdate(SQLModel):
    username: Optional[str] = Field(
        None, min_length=4, max_length=20, regex=r"^[a-zA-Z0-9_]+$"
    )
    password: Optional[str] = Field(None, min_length=8)


class UserLogin(SQLModel):
    username: str
    password: str = Field(..., min_length=8)


class Token(BaseModel):
    token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None
