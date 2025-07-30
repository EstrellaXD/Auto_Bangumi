from datetime import datetime
from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from .bangumi import Bangumi


class Torrent(SQLModel, table=True):
    url: str = Field(primary_key=True, alias="url")
    name: str = Field(default="", alias="name")
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    downloaded: bool = Field(default=False, alias="downloaded")
    renamed: bool = Field(default=False, alias="renamed")
    download_uid: str | None = Field(default=None, alias="duid", index=True)
    bangumi_official_title: str | None = Field(
        default=None, index=True, alias="bangumi_title"
    )
    bangumi_season: int | None = Field(default=None, index=True, alias="bangumi_season")
    rss_url: str | None = Field(default=None, alias="ruid", index=True)
    # TODO: 添加外键字段 rss_id 和 bangumi_id 替代当前的字符串引用
    homepage: str | None = Field(default=None, alias="homepage")


class TorrentDownloadInfo(BaseModel):
    eta: int | None = Field(default=60, alias="eta")
    save_path: str = Field(default="", alias="save_path")
    completed: int = Field(default=0, alias="completed")


class TorrentUpdate(BaseModel):
    downloaded: bool = Field(default=False, alias="downloaded")


class EpisodeFile(BaseModel):
    media_path: str = Field(...)
    group: str | None = Field(default=None)
    title: str = Field(...)
    season: int = Field(default=1)
    episode: int = Field(default=0)
    suffix: str = Field(..., regex=r"(?i)\.(mkv|mp4)$")


class SubtitleFile(BaseModel):
    media_path: str = Field(...)
    group: str | None = Field(default=None)
    title: str = Field(...)
    season: int = Field(default=1)
    episode: int = Field(default=0)
    language: str = Field(..., regex=r"(zh|zh-tw)")
    suffix: str = Field(..., regex=r"(?i)\.(ass|srt)$")


