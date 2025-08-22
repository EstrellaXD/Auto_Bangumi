from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class BangumiBase(SQLModel):
    official_title: str = Field(default="", alias="official_title", title="番剧中文名")
    year: str | None = Field(default=None, alias="year", title="番剧年份")
    title_raw: str = Field(default="title_raw", alias="title_raw", title="番剧原名")
    season: int = Field(default=1, alias="season", title="番剧季度")
    season_raw: str | None = Field(
        default=None, alias="season_raw", title="番剧季度原名"
    )
    group_name: str | None = Field(default=None, alias="group_name", title="字幕组")
    dpi: str | None = Field(default=None, alias="dpi", title="分辨率")
    source: str | None = Field(default=None, alias="source", title="来源")
    subtitle: str | None = Field(default=None, alias="subtitle", title="字幕")
    eps_collect: bool = Field(default=False, alias="eps_collect", title="是否已收集")
    offset: int = Field(default=0, alias="offset", title="番剧偏移量")
    include_filter: str = Field(
        default="", alias="include_filter", title="番剧包含过滤器"
    )
    exclude_filter: str = Field(
        default="", alias="exclude_filter", title="番剧排除过滤器"
    )
    parser: str = Field(default="mikan", alias="parser", title="番剧解析器")
    tmdb_id: str | None = Field(default=None, alias="tmdb_id", title="番剧TMDB ID")
    bangumi_id: str | None = Field(
        default=None, alias="bangumi_id", title="番剧Bangumi ID"
    )
    mikan_id: str | None = Field(default=None, alias="mikan_id", title="番剧Mikan ID")
    rss_link: str = Field(default="", alias="rss_link", title="番剧RSS链接")
    poster_link: str = Field(default="", alias="poster_link", title="番剧海报链接")
    rule_name: str | None = Field(default=None, alias="rule_name", title="番剧规则名")
    added: bool = Field(default=False, alias="added", title="是否已添加")
    deleted: bool = Field(default=False, alias="deleted", title="是否已删除")


class Bangumi(BangumiBase, table=True):
    id: int = Field(default=None, primary_key=True)


class BangumiUpdate(BangumiBase):
    id: int = Field(default=None)
    pass


class Message(BaseModel):
    title: str = Field(..., alias="title", title="标题")
    message: str = Field(default="", alias="message", title="消息")
    season: str = Field(default="",  alias="season", title="番剧季度")
    episode: str = Field(default="", alias="episode", title="番剧集数")
    poster_path: str = Field(default="", alias="poster_path", title="番剧海报路径")
    file: bytes | None = Field(default=None, alias="file", title="文件内容")


class Episode(BaseModel):
    title_en: str = Field(default="", alias="title_en", title="英文标题")
    title_zh: str = Field(default="", alias="title_zh", title="中文标题")
    title_jp: str = Field(default="", alias="title_jp", title="日文标题")
    title_romaji: str = Field(default="", alias="title_romaji", title="罗马音标题")
    season: int = Field(default=1, ge=0, alias="season", title="番剧季度")
    season_raw: str = Field(default="", alias="season_raw", title="番剧季度原名")
    episode: int = Field(default=0, ge=0, alias="episode", title="番剧集数")
    sub: str = Field(default="", alias="sub", title="字幕语言")
    sub_type: str = Field(default="", alias="sub_type", title="字幕类型")
    group: str = Field(default="", alias="group", title="字幕组")
    resolution: str = Field(default="", alias="resolution", title="分辨率")
    source: str = Field(default="", alias="source", title="视频来源")
    audio_info: list[str] = Field(
        default_factory=list, alias="audio_info", title="音频信息"
    )
    video_info: list[str] = Field(
        default_factory=list, alias="video_info", title="视频信息"
    )

    def get_title(self) -> str:
        if self.title_zh:
            return self.title_zh
        if self.title_en:
            return self.title_en
        if self.title_jp:
            return self.title_jp
        return ""
