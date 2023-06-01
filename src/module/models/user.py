from pydantic import BaseModel, Field


class User(BaseModel):
    username: str = Field(
        "admin", min_length=4, max_length=20, regex=r"^[a-zA-Z0-9_]+$"
    )
    password: str = Field("adminadmin", min_length=8)


class UserLogin(BaseModel):
    username: str
    password: str = Field(..., min_length=8)


class Token(BaseModel):
    token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None
