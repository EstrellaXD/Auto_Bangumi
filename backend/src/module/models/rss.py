from sqlmodel import SQLModel, Field
from typing import Optional


class RSSItem(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True, alias="id")
    name: Optional[str] = Field(None, alias="name")
    url: str = Field("https://mikanani.me", alias="url")
    aggregate: bool = Field(True, alias="aggregate")
    parser: str = Field("mikan", alias="parser")
    enabled: bool = Field(True, alias="enabled")


class RSSUpdate(SQLModel):
    name: Optional[str] = Field(None, alias="name")
    url: Optional[str] = Field("https://mikanani.me", alias="url")
    aggregate: Optional[bool] = Field(True, alias="aggregate")
    parser: Optional[str] = Field("mikan", alias="parser")
    enabled: Optional[bool] = Field(True, alias="enabled")
