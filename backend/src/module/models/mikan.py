from pydantic import BaseModel, Field


class MikanInfo(BaseModel):
    id: str = Field(default="", alias="id", title="Mikan ID")
    official_title: str = Field(default="", alias="official_title", title="官方标题")
    season: int = Field(default=1, alias="season", title="季度")
    poster_link: str = Field(default="", alias="poster_link", title="海报链接")
