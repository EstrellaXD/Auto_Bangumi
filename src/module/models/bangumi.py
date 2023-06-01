from pydantic import BaseModel, Field
from dataclasses import dataclass


class BangumiData(BaseModel):
    id: int = Field(0, alias="id", title="番剧ID")
    official_title: str = Field("official_title", alias="official_title", title="番剧中文名")
    year: str | None = Field(None, alias="year", title="番剧年份")
    title_raw: str = Field("title_raw", alias="title_raw", title="番剧原名")
    season: int = Field(1, alias="season", title="番剧季度")
    season_raw: str | None = Field(None, alias="season_raw", title="番剧季度原名")
    group_name: str | None = Field(None, alias="group_name", title="字幕组")
    dpi: str | None = Field(None, alias="dpi", title="分辨率")
    source: str | None = Field(None, alias="source", title="来源")
    subtitle: str | None = Field(None, alias="subtitle", title="字幕")
    eps_collect: bool = Field(False, alias="eps_collect", title="是否已收集")
    offset: int = Field(0, alias="offset", title="番剧偏移量")
    filter: list[str] = Field(["720", "\\d+-\\d+"], alias="filter", title="番剧过滤器")
    rss_link: list[str] = Field([], alias="rss_link", title="番剧RSS链接")
    poster_link: str | None = Field(None, alias="poster_link", title="番剧海报链接")
    added: bool = Field(False, alias="added", title="是否已添加")
    rule_name: str | None = Field(None, alias="rule_name", title="番剧规则名")
    save_path: str | None = Field(None, alias="save_path", title="番剧保存路径")
    deleted: bool = Field(False, alias="deleted", title="是否已删除")


class Notification(BaseModel):
    official_title: str = Field(..., alias="official_title", title="番剧名")
    season: int = Field(..., alias="season", title="番剧季度")
    episode: int = Field(..., alias="episode", title="番剧集数")


@dataclass
class Episode:
    title_en: str | None
    title_zh: str | None
    title_jp: str | None
    season: int
    season_raw: str
    episode: int
    sub: str
    group: str
    resolution: str
    source: str


@dataclass
class SeasonInfo(dict):
    official_title: str
    title_raw: str
    season: int
    season_raw: str
    group: str
    filter: list | None
    offset: int | None
    dpi: str
    source: str
    subtitle: str
    added: bool
    eps_collect: bool
