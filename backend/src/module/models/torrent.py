from typing import Optional

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class Torrent(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True, alias="id")
    bangumi_id: Optional[int] = Field(
        default=None, alias="refer_id", foreign_key="bangumi.id", index=True
    )
    rss_id: Optional[int] = Field(
        default=None, alias="rss_id", foreign_key="rssitem.id", index=True
    )
    name: str = Field(default="", alias="name")
    url: str = Field(default="https://example.com/torrent", alias="url", index=True)
    homepage: Optional[str] = Field(default=None, alias="homepage")
    downloaded: bool = Field(default=False, alias="downloaded")
    qb_hash: Optional[str] = Field(default=None, alias="qb_hash", index=True)
    # 种子实际添加到的下载器实例
    downloader_id: str = Field(default="default", alias="downloader_id")


class EpisodeFile(BaseModel):
    media_path: str = Field(default=...)
    group: str | None = Field(default=None)
    title: str = Field(default=...)
    season: int = Field(default=...)
    episode: int | float = Field(default=None)
    suffix: str = Field(default=..., regex=r"\.(mkv|mp4|MKV|MP4)$")
    episode_type: str = Field(default="episode")  # "episode" | "movie" | "special"


class SubtitleFile(BaseModel):
    media_path: str = Field(default=...)
    group: str | None = Field(default=None)
    title: str = Field(default=...)
    season: int = Field(default=...)
    episode: int | float = Field(default=None)
    language: str = Field(default=..., regex=r"(zh|zh-tw)")
    suffix: str = Field(default=..., regex=r"\.(ass|srt|ASS|SRT)$")
    episode_type: str = Field(default="episode")  # "episode" | "movie" | "special"
