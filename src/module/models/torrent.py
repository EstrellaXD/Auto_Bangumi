from pydantic import BaseModel, Field


class TorrentInfo(BaseModel):
    name: str = Field(...)
    link: str = Field(...)


class FileSet(BaseModel):
    media_path: str = Field(...)
    sc_subtitle: str | None = Field(None)
    tc_subtitle: str | None = Field(None)
