from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from .bangumi import Bangumi


class Torrent(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True, alias="id")
    bangumi_id: int | None = Field(
        default=None, alias="refer_id", foreign_key="bangumi.id"
    )
    rss_id: int | None = Field(default=None, alias="rss_id", foreign_key="rssitem.id")
    name: str = Field(default="", alias="name")
    url: str = Field("https://example.com/torrent", alias="url", unique=True)
    homepage: str | None = Field(default=None, alias="homepage")
    downloaded: bool = Field(default=False, alias="downloaded")


class TorrentUpdate(SQLModel):
    downloaded: bool = Field(default=False, alias="downloaded")


class EpisodeFile(BaseModel):
    media_path: str = Field(...)
    group: str | None = Field(default=None)
    title: str = Field(...)
    season: int = Field(...)
    episode: int | float = Field(default=0)
    suffix: str = Field(..., regex=r"(?i)\.(mkv|mp4)$")


class SubtitleFile(BaseModel):
    media_path: str = Field(...)
    group: str | None = Field(default=None)
    title: str = Field(...)
    season: int = Field(...)
    episode: int | float = Field(default=0)
    language: str = Field(..., regex=r"(zh|zh-tw)")
    suffix: str = Field(..., regex=r"(?i)\.(ass|srt)$")


class RenamerInfo(BaseModel):
    torrent: Torrent | str
    bangumi: Bangumi | None
    hash: str
    content: list[str] = Field(default=[])
    save_path: str = Field("")
