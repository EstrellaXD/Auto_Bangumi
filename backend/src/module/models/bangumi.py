from dataclasses import dataclass

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class Bangumi(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    official_title: str = Field(
        default="official_title", alias="official_title", title="番剧中文名"
    )
    year: str | None = Field(default=..., alias="year", title="番剧年份")
    title_raw: str = Field(
        default="title_raw", alias="title_raw", title="番剧原名", index=True
    )
    season: int = Field(default=1, alias="season", title="番剧季度")
    season_raw: str | None = Field(
        default=..., alias="season_raw", title="番剧季度原名"
    )
    group_name: str | None = Field(default=..., alias="group_name", title="字幕组")
    dpi: str | None = Field(default=..., alias="dpi", title="分辨率")
    source: str | None = Field(default=..., alias="source", title="来源")
    subtitle: str | None = Field(default=..., alias="subtitle", title="字幕")
    eps_collect: bool = Field(default=False, alias="eps_collect", title="是否已收集")
    episode_offset: int = Field(default=0, alias="episode_offset", title="集数偏移量")
    season_offset: int = Field(default=0, alias="season_offset", title="季度偏移量")
    filter: str = Field(default="720,\\d+-\\d+", alias="filter", title="番剧过滤器")
    rss_link: str = Field(default="", alias="rss_link", title="番剧RSS链接")
    poster_link: str | None = Field(
        default=..., alias="poster_link", title="番剧海报链接"
    )
    added: bool = Field(default=False, alias="added", title="是否已添加")
    rule_name: str | None = Field(default=..., alias="rule_name", title="番剧规则名")
    save_path: str | None = Field(default=..., alias="save_path", title="番剧保存路径")
    deleted: bool = Field(
        default=False, alias="deleted", title="是否已删除", index=True
    )
    archived: bool = Field(
        default=False, alias="archived", title="是否已归档", index=True
    )
    air_weekday: int | None = Field(default=None, alias="air_weekday", title="放送星期")
    weekday_locked: bool = Field(
        default=False, alias="weekday_locked", title="放送星期锁定"
    )
    needs_review: bool = Field(default=False, alias="needs_review", title="需要检查")
    needs_review_reason: str | None = Field(
        default=None, alias="needs_review_reason", title="检查原因"
    )
    suggested_season_offset: int | None = Field(
        default=None, alias="suggested_season_offset", title="建议季度偏移"
    )
    suggested_episode_offset: int | None = Field(
        default=None, alias="suggested_episode_offset", title="建议集数偏移"
    )
    title_aliases: str | None = Field(
        default=None, alias="title_aliases", title="标题别名"
    )  # JSON list: ["alt_title_1", "alt_title_2"]
    preferred_group: str | None = Field(
        default=None, alias="preferred_group", title="偏好字幕组"
    )
    preferred_resolution: str | None = Field(
        default=None, alias="preferred_resolution", title="偏好分辨率"
    )
    episode_type: str = Field(
        default="episode", alias="episode_type", title="剧集类型"
    )  # "episode" | "movie" | "special"
    # 为空时用默认下载器实例（plugins.slots.downloader）
    downloader_id: str | None = Field(
        default=None, alias="downloader_id", title="下载器实例"
    )


class BangumiUpdate(SQLModel):
    official_title: str = Field(
        default="official_title", alias="official_title", title="番剧中文名"
    )
    year: str | None = Field(default=..., alias="year", title="番剧年份")
    title_raw: str = Field(default="title_raw", alias="title_raw", title="番剧原名")
    season: int = Field(default=1, alias="season", title="番剧季度")
    season_raw: str | None = Field(
        default=..., alias="season_raw", title="番剧季度原名"
    )
    group_name: str | None = Field(default=..., alias="group_name", title="字幕组")
    dpi: str | None = Field(default=..., alias="dpi", title="分辨率")
    source: str | None = Field(default=..., alias="source", title="来源")
    subtitle: str | None = Field(default=..., alias="subtitle", title="字幕")
    eps_collect: bool = Field(default=False, alias="eps_collect", title="是否已收集")
    episode_offset: int = Field(default=0, alias="episode_offset", title="集数偏移量")
    season_offset: int = Field(default=0, alias="season_offset", title="季度偏移量")
    filter: str = Field(default="720,\\d+-\\d+", alias="filter", title="番剧过滤器")
    rss_link: str = Field(default="", alias="rss_link", title="番剧RSS链接")
    poster_link: str | None = Field(
        default=..., alias="poster_link", title="番剧海报链接"
    )
    added: bool = Field(default=False, alias="added", title="是否已添加")
    rule_name: str | None = Field(default=..., alias="rule_name", title="番剧规则名")
    save_path: str | None = Field(default=..., alias="save_path", title="番剧保存路径")
    downloader_id: str | None = Field(
        default=None, alias="downloader_id", title="下载器实例"
    )
    deleted: bool = Field(default=False, alias="deleted", title="是否已删除")
    archived: bool = Field(default=False, alias="archived", title="是否已归档")
    air_weekday: int | None = Field(default=None, alias="air_weekday", title="放送星期")
    weekday_locked: bool = Field(
        default=False, alias="weekday_locked", title="放送星期锁定"
    )
    needs_review: bool = Field(default=False, alias="needs_review", title="需要检查")
    needs_review_reason: str | None = Field(
        default=None, alias="needs_review_reason", title="检查原因"
    )
    title_aliases: str | None = Field(
        default=None, alias="title_aliases", title="标题别名"
    )
    preferred_group: str | None = Field(
        default=None, alias="preferred_group", title="偏好字幕组"
    )
    preferred_resolution: str | None = Field(
        default=None, alias="preferred_resolution", title="偏好分辨率"
    )
    episode_type: str = Field(
        default="episode", alias="episode_type", title="剧集类型"
    )  # "episode" | "movie" | "special"


class Notification(BaseModel):
    official_title: str = Field(default=..., alias="official_title", title="番剧名")
    season: int = Field(default=..., alias="season", title="番剧季度")
    # int | float：总集篇等半集（12.5）在通知里保留小数 (#667)
    episode: int | float = Field(default=..., alias="episode", title="番剧集数")
    poster_path: str | None = Field(
        default=None, alias="poster_path", title="番剧海报路径"
    )


@dataclass(slots=True)
class Episode:
    title_en: str | None
    title_zh: str | None
    title_jp: str | None
    season: int
    season_raw: str
    episode: int
    sub: str | None
    group: str
    resolution: str | None
    source: str | None
    episode_type: str = "episode"  # "episode" | "movie" | "special"
    is_movie: bool = False

    def __post_init__(self) -> None:
        """Keep the legacy movie flag and the typed classifier in sync."""
        if self.is_movie:
            self.episode_type = "movie"
        elif self.episode_type == "movie":
            self.is_movie = True
