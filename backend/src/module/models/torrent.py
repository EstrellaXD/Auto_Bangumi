from typing import Optional

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class Torrent(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True, alias="id")
    bangumi_id: Optional[int] = Field(
        None, alias="refer_id", foreign_key="bangumi.id", index=True
    )
    rss_id: Optional[int] = Field(
        None, alias="rss_id", foreign_key="rssitem.id", index=True
    )
    name: str = Field("", alias="name")
    url: str = Field("https://example.com/torrent", alias="url", index=True)
    homepage: Optional[str] = Field(None, alias="homepage")
    downloaded: bool = Field(False, alias="downloaded")
    qb_hash: Optional[str] = Field(None, alias="qb_hash", index=True)
    # 种子实际添加到的下载器实例
    downloader_id: str = Field("default", alias="downloader_id")


class EpisodeFile(BaseModel):
    media_path: str = Field(...)
    group: str | None = Field(None)
    title: str = Field(...)
    season: int = Field(...)
    episode: int | float = Field(None)
    suffix: str = Field(..., regex=r"\.(mkv|mp4|MKV|MP4)$")
    episode_type: str = Field("episode")  # "episode" | "movie" | "special"


class SubtitleFile(BaseModel):
    media_path: str = Field(...)
    group: str | None = Field(None)
    title: str = Field(...)
    season: int = Field(...)
    episode: int | float = Field(None)
    language: str = Field(..., regex=r"(zh|zh-tw)")
    suffix: str = Field(..., regex=r"\.(ass|srt|ASS|SRT)$")
    episode_type: str = Field("episode")  # "episode" | "movie" | "special"
