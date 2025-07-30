from dataclasses import dataclass

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class BangumiBase(SQLModel):
    official_title: str = Field(default="official_title", alias="official_title", title="番剧中文名")
    year: str | None = Field(default=None, alias="year", title="番剧年份")
    title_raw: str = Field(default="title_raw", alias="title_raw", title="番剧原名")
    season: int = Field(default=1, alias="season", title="番剧季度")
    season_raw: str | None = Field(default=None, alias="season_raw", title="番剧季度原名")
    group_name: str | None = Field(default=None, alias="group_name", title="字幕组")
    dpi: str | None = Field(default=None, alias="dpi", title="分辨率")
    source: str | None = Field(default=None, alias="source", title="来源")
    subtitle: str | None = Field(default=None, alias="subtitle", title="字幕")
    eps_collect: bool = Field(default=False, alias="eps_collect", title="是否已收集")
    offset: int = Field(default=0, alias="offset", title="番剧偏移量")
    include_filter: str = Field(default="", alias="include_filter", title="番剧包含过滤器")
    exclude_filter: str = Field(default="", alias="exclude_filter", title="番剧排除过滤器")
    tmdb_id: str | None = Field(default=None, alias="tmdb_id", title="番剧TMDB ID")
    bangumi_id: str | None = Field(default=None, alias="bangumi_id", title="番剧Bangumi ID")
    mikan_id: str | None = Field(default=None, alias="mikan_id", title="番剧Mikan ID")
    # filter: str = Field(default="", alias="filter", title="番剧过滤器")
    # 感觉是不是与 rss 表用外键关联更好
    rss_link: str = Field(default="", alias="rss_link", title="番剧RSS链接")
    poster_link: str = Field(default="", alias="poster_link", title="番剧海报链接")
    added: bool = Field(default=False, alias="added", title="是否已添加")
    rule_name: str | None = Field(default=None, alias="rule_name", title="番剧规则名")
    deleted: bool = Field(default=False, alias="deleted", title="是否已删除")


class Bangumi(BangumiBase, table=True):
    id: int = Field(default=None, primary_key=True)

class BangumiUpdate(BangumiBase):
    # 覆盖特定字段的默认值
    exclude_filter: str = Field(default="720,\\d+-\\d+", alias="exclude_filter", title="番剧排除过滤器")
    deleted: bool = Field(default=False, alias="deleted", title="是否已删除")


class Notification(BaseModel):
    title: str = Field(..., alias="title", title="标题")
    message: str = Field(default=None, alias="message", title="消息")
    season: int = Field(default=0, alias="season", title="番剧季度")
    episode: str = Field(default="0", alias="episode", title="番剧集数")
    poster_path: str = Field(default="", alias="poster_path", title="番剧海报路径")

@dataclass
class Episode():
    title_en: str
    title_zh: str
    title_jp: str
    season: int
    season_raw: str
    episode: int
    sub: str
    group: str
    resolution: str
    source: str
    audio_info: list[str]
    video_info: list[str]


