from pydantic import BaseModel, Field


class TorrentInfo(BaseModel):
    name: str = Field(...)
    link: str = Field(...)
    homepage: str | None = Field(None)
    poster_link: str = Field(...)
    official_title: str = Field(...)


class FileSet(BaseModel):
    media_path: str = Field(...)
    sc_subtitle: str | None = Field(None)
    tc_subtitle: str | None = Field(None)


class EpisodeFile(BaseModel):
    media_path: str = Field(...)
    group: str | None = Field(None)
    title: str = Field(...)
    season: int = Field(...)
    episode: int = Field(None)
    suffix: str = Field(..., regex=r"\.(mkv|mp4|MKV|MP4)$")


class SubtitleFile(BaseModel):
    media_path: str = Field(...)
    group: str | None = Field(None)
    title: str = Field(...)
    season: int = Field(...)
    episode: int = Field(None)
    language: str = Field(..., regex=r"(zh|zh-tw)")
    suffix: str = Field(..., regex=r"\.(ass|srt|ASS|SRT)$")

