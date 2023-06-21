from pydantic import BaseModel, Field


class RSSItem(BaseModel):
    id: int = Field(0, alias="id", title="id")
    item_path: str = Field("example path", alias="item_path")
    url: str = Field("https://mikanani.me", alias="url")
    combine: bool = Field(True, alias="combine")
    enabled: bool = Field(True, alias="enabled")


class TorrentData(BaseModel):
    id: int = Field(0, alias="id")
    rss_id: int = Field(0, alias="rss_id")
    name: str = Field("", alias="name")
    url: str = Field("https://example.com/torrent", alias="url")
    save_path: str = Field("path/to/save", alias="save_path")
