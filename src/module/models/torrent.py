from pydantic import BaseModel, Field


class TorrentInfo(BaseModel):
    name: str = Field(...)
    link: str = Field(...)


class FileSet(BaseModel):
    media_path: str = Field(...)
    sc_subtitle: str | None = Field(None)
    tc_subtitle: str | None = Field(None)


class EpisodeFile(BaseModel):
    group: str | None = Field(None)
    title: str = Field(...)
    season: int = Field(...)
    episode: int = Field(None)
    suffix: str = Field(..., regex=r"\.(mkv|mp4)$")


class SubtitleFile(BaseModel):
    group: str | None = Field(None)
    title: str = Field(...)
    season: int = Field(...)
    episode: int = Field(None)
    language: str = Field(..., regex=r"(zh|zh-tw)")
    suffix: str = Field(..., regex=r"\.(ass|srt)$")

