from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class UserBase(BaseModel):
    username: str = Field(..., min_length=4, max_length=20, regex=r"^[a-zA-Z0-9_]+$")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(UserBase):
    password: str = Field(..., min_length=8)


class User(UserBase):
    id: int = Field(..., alias="_id")
    password: str = Field(..., min_length=8)


class UserInDB(UserBase):
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    username: str
    password: str = Field(..., min_length=8)


class Token(BaseModel):
    token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None