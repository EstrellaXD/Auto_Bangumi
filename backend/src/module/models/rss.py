from typing import Optional

from sqlmodel import Field, SQLModel


class RSSItem(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True, alias="id")
    name: Optional[str] = Field(default=None, alias="name")
    url: str = Field(default="https://mikanani.me", alias="url", index=True)
    aggregate: bool = Field(default=False, alias="aggregate")
    parser: str = Field(default="mikan", alias="parser")
    enabled: bool = Field(default=True, alias="enabled")
    connection_status: Optional[str] = Field(default=None, alias="connection_status")
    last_checked_at: Optional[str] = Field(default=None, alias="last_checked_at")
    last_error: Optional[str] = Field(default=None, alias="last_error")
    # 由此订阅新建的规则继承；为空时用默认下载器实例
    downloader_id: Optional[str] = Field(default=None, alias="downloader_id")


class RSSUpdate(SQLModel):
    name: Optional[str] = Field(default=None, alias="name")
    url: Optional[str] = Field(default="https://mikanani.me", alias="url")
    aggregate: Optional[bool] = Field(default=True, alias="aggregate")
    parser: Optional[str] = Field(default="mikan", alias="parser")
    enabled: Optional[bool] = Field(default=True, alias="enabled")
    downloader_id: Optional[str] = Field(default=None, alias="downloader_id")
