from sqlmodel import SQLModel, Field
from typing import Optional


class RSSItem(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True, alias="id")
    item_path: str = Field("example path", alias="item_path")
    url: str = Field("https://mikanani.me", alias="url")
    combine: bool = Field(True, alias="combine")
    enabled: bool = Field(True, alias="enabled")


class RSSUpdate(SQLModel):
    item_path: Optional[str] = Field("example path", alias="item_path")
    url: Optional[str] = Field("https://mikanani.me", alias="url")
    combine: Optional[bool] = Field(True, alias="combine")
    enabled: Optional[bool] = Field(True, alias="enabled")




