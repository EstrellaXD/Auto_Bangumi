from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class Bangumi(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    official_title: str = Field(
        default="official_title", alias="official_title", title="番剧中文名"
    )
    year: Optional[str] = Field(alias="year", title="番剧年份")
    title_raw: str = Field(
        default="title_raw", alias="title_raw", title="番剧原名", index=True
    )
    season: int = Field(default=1, alias="season", title="番剧季度")
    season_raw: Optional[str] = Field(alias="season_raw", title="番剧季度原名")
    group_name: Optional[str] = Field(alias="group_name", title="字幕组")
    dpi: Optional[str] = Field(alias="dpi", title="分辨率")
    source: Optional[str] = Field(alias="source", title="来源")
    subtitle: Optional[str] = Field(alias="subtitle", title="字幕")
    eps_collect: bool = Field(default=False, alias="eps_collect", title="是否已收集")
    episode_offset: int = Field(default=0, alias="episode_offset", title="集数偏移量")
    season_offset: int = Field(default=0, alias="season_offset", title="季度偏移量")
    filter: str = Field(default="720,\\d+-\\d+", alias="filter", title="番剧过滤器")
    rss_link: str = Field(default="", alias="rss_link", title="番剧RSS链接")
    poster_link: Optional[str] = Field(alias="poster_link", title="番剧海报链接")
    added: bool = Field(default=False, alias="added", title="是否已添加")
    rule_name: Optional[str] = Field(alias="rule_name", title="番剧规则名")
    save_path: Optional[str] = Field(alias="save_path", title="番剧保存路径")
    deleted: bool = Field(False, alias="deleted", title="是否已删除", index=True)
    archived: bool = Field(
        default=False, alias="archived", title="是否已归档", index=True
    )
    air_weekday: Optional[int] = Field(
        default=None, alias="air_weekday", title="放送星期"
    )
    needs_review: bool = Field(default=False, alias="needs_review", title="需要检查")
    needs_review_reason: Optional[str] = Field(
        default=None, alias="needs_review_reason", title="检查原因"
    )
    suggested_season_offset: Optional[int] = Field(
        default=None, alias="suggested_season_offset", title="建议季度偏移"
    )
    suggested_episode_offset: Optional[int] = Field(
        default=None, alias="suggested_episode_offset", title="建议集数偏移"
    )
    title_aliases: Optional[str] = Field(
        default=None, alias="title_aliases", title="标题别名"
    )  # JSON list: ["alt_title_1", "alt_title_2"]


class BangumiUpdate(SQLModel):
    official_title: str = Field(
        default="official_title", alias="official_title", title="番剧中文名"
    )
    year: Optional[str] = Field(alias="year", title="番剧年份")
    title_raw: str = Field(default="title_raw", alias="title_raw", title="番剧原名")
    season: int = Field(default=1, alias="season", title="番剧季度")
    season_raw: Optional[str] = Field(alias="season_raw", title="番剧季度原名")
    group_name: Optional[str] = Field(alias="group_name", title="字幕组")
    dpi: Optional[str] = Field(alias="dpi", title="分辨率")
    source: Optional[str] = Field(alias="source", title="来源")
    subtitle: Optional[str] = Field(alias="subtitle", title="字幕")
    eps_collect: bool = Field(default=False, alias="eps_collect", title="是否已收集")
    episode_offset: int = Field(default=0, alias="episode_offset", title="集数偏移量")
    season_offset: int = Field(default=0, alias="season_offset", title="季度偏移量")
    filter: str = Field(default="720,\\d+-\\d+", alias="filter", title="番剧过滤器")
    rss_link: str = Field(default="", alias="rss_link", title="番剧RSS链接")
    poster_link: Optional[str] = Field(alias="poster_link", title="番剧海报链接")
    added: bool = Field(default=False, alias="added", title="是否已添加")
    rule_name: Optional[str] = Field(alias="rule_name", title="番剧规则名")
    save_path: Optional[str] = Field(alias="save_path", title="番剧保存路径")
    deleted: bool = Field(False, alias="deleted", title="是否已删除")
    archived: bool = Field(default=False, alias="archived", title="是否已归档")
    air_weekday: Optional[int] = Field(
        default=None, alias="air_weekday", title="放送星期"
    )
    needs_review: bool = Field(default=False, alias="needs_review", title="需要检查")
    needs_review_reason: Optional[str] = Field(
        default=None, alias="needs_review_reason", title="检查原因"
    )
    title_aliases: Optional[str] = Field(
        default=None, alias="title_aliases", title="标题别名"
    )


class Notification(BaseModel):
    official_title: str = Field(..., alias="official_title", title="番剧名")
    season: int = Field(..., alias="season", title="番剧季度")
    episode: int = Field(..., alias="episode", title="番剧集数")
    poster_path: Optional[str] = Field(None, alias="poster_path", title="番剧海报路径")


@dataclass(slots=True)
class Episode:
    title_en: Optional[str]
    title_zh: Optional[str]
    title_jp: Optional[str]
    season: int
    season_raw: str
    episode: int
    sub: str
    group: str
    resolution: str
    source: str


@dataclass(slots=True)
class SeasonInfo:
    official_title: str
    title_raw: str
    season: int
    season_raw: str
    group: str
    filter: list | None
    episode_offset: int | None
    season_offset: int | None
    dpi: str
    source: str
    subtitle: str
    added: bool
    eps_collect: bool
