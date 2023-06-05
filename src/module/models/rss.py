from pydantic import BaseModel, Field


class RSSTorrents(BaseModel):
    name: str = Field(..., alias="item_path")
    url: str = Field(..., alias="url")
    analyze: bool = Field(..., alias="analyze")
    enabled: bool = Field(..., alias="enabled")
    torrents: list[str] = Field(..., alias="torrents")

