from datetime import datetime, timezone

from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from .bangumi import Episode


class Torrent(SQLModel, table=True):
    url: str = Field(primary_key=True, alias="url")
    name: str = Field(default="", alias="name")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    downloaded: bool = Field(default=False, alias="downloaded")
    renamed: bool = Field(default=False, alias="renamed")
    download_uid: str | None = Field(default=None, alias="duid", index=True)
    bangumi_official_title: str = Field(default="", index=True, alias="bangumi_title")
    bangumi_season: int = Field(default=1, index=True, alias="bangumi_season")
    rss_link: str = Field(default="", alias="ruid", index=True)
    homepage: str | None = Field(default=None, alias="homepage")


class TorrentDownloadInfo(BaseModel):
    eta: int | None = Field(default=60, alias="eta")
    save_path: str = Field(default="", alias="save_path")
    completed: int = Field(default=0, alias="completed")


class TorrentUpdate(BaseModel):
    downloaded: bool = Field(default=False, alias="downloaded")


class EpisodeFile(Episode):
    media_path: str = Field(...)
    title: str = Field(...)
    suffix: str = Field(..., regex=r"(?i)\.(mkv|mp4)$")


class SubtitleFile(EpisodeFile):
    language: str = Field(..., regex=r"(zh|zh-tw)")
    suffix: str = Field(..., regex=r"(?i)\.(ass|srt)$")
