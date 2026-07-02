"""aria2 gid <-> bangumi 关联表模型。

aria2 没有 qBittorrent 的 tag/category 概念，只能通过本地记录把下载任务的
gid 关联回 bangumi_id（用于续传后的 offset 查找）以及伪造的 category（用于
torrents_info 的分类过滤）和 dedup_key（用于识别"已经添加过"）。
"""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class Aria2Gid(SQLModel, table=True):
    """aria2 下载任务 (gid) 到 bangumi / category / 去重键 的本地映射。"""

    __tablename__ = "aria2_gid"

    gid: str = Field(primary_key=True)
    bangumi_id: Optional[int] = Field(default=None, foreign_key="bangumi.id")
    category: Optional[str] = None
    dedup_key: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
