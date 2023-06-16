from pydantic import BaseModel, Field


class RSSItem(BaseModel):
    id: int = Field(0, alias="id", title="id")
    item_path: str = Field("example path", alias="item_path")
    url: str = Field("https://mikanani.me", alias="url")
    combine: bool = Field(True, alias="combine")
    enabled: bool = Field(True, alias="enabled")


class TorrentData(BaseModel):
    id: int = Field(0, alias="id")
    name: str = Field(..., alias="name")
    url: str = Field(..., alias="url")
    matched: bool = Field(..., alias="matched")
    downloaded: bool = Field(..., alias="downloaded")
    save_path: str = Field(..., alias="save_path")
