from sqlmodel import SQLModel, Field
from typing import Optional


class RSSItem(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True, alias="id")
    item_path: Optional[str] = Field(None, alias="item_path")
    url: str = Field("https://mikanani.me", alias="url")
    combine: bool = Field(True, alias="combine")
    parser: str = Field("mikan", alias="parser")
    enabled: bool = Field(True, alias="enabled")


class RSSUpdate(SQLModel):
    item_path: Optional[str] = Field("example path", alias="item_path")
    url: Optional[str] = Field("https://mikanani.me", alias="url")
    combine: Optional[bool] = Field(True, alias="combine")
    parser: Optional[str] = Field("mikan", alias="parser")
    enabled: Optional[bool] = Field(True, alias="enabled")
