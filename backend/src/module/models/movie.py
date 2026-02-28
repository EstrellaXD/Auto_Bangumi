from typing import Optional

from sqlmodel import Field, SQLModel


class Movie(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    official_title: str = Field(
        default="official_title", alias="official_title", title="剧场版名"
    )
    title_raw: str | None = Field(
        default=None, alias="title_raw", title="剧场版原名", index=True
    )
    year: int | None = Field(default=None, alias="year", title="年份")
    group_name: str | None = Field(default=None, alias="group_name", title="字幕组")
    dpi: str | None = Field(default=None, alias="dpi", title="分辨率")
    source: str | None = Field(default=None, alias="source", title="来源")
    subtitle: str | None = Field(default=None, alias="subtitle", title="字幕")
    poster_link: str | None = Field(default=None, alias="poster_link", title="海报链接")
    rss_link: str | None = Field(default=None, alias="rss_link", title="RSS链接")
    added: bool = Field(default=False, alias="added", title="是否已添加")
    deleted: bool = Field(
        default=False, alias="deleted", title="是否已删除", index=True
    )
    save_path: str | None = Field(default=None, alias="save_path", title="保存路径")
    rule_name: str | None = Field(default=None, alias="rule_name", title="规则名")
    filter: str = Field(default="", alias="filter", title="过滤器")


class MovieUpdate(SQLModel):
    official_title: str | None = None
    title_raw: str | None = None
    year: int | None = None
    group_name: str | None = None
    dpi: str | None = None
    source: str | None = None
    subtitle: str | None = None
    poster_link: str | None = None
    rss_link: str | None = None
    save_path: str | None = None
    filter: str | None = None
