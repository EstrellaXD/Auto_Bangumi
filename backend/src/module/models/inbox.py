"""站内通知（通知中心）消息模型。

一行 = 一条通知。``kind`` + JSON ``payload`` 供前端按语言渲染文案，
``title``/``body`` 为 ``describe()`` 生成的中文兜底文案（未知 kind 时直接展示）。
时间戳沿用 RSSItem 的约定：UTC ISO-8601 字符串（字典序即时间序）。
"""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class InboxMessage(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    kind: str = Field("", index=True)
    severity: str = Field("info")  # info | warning | error
    title: str = Field("")
    body: str = Field("")
    payload: Optional[str] = Field(None)  # JSON 字符串
    dedup_key: Optional[str] = Field(None, index=True)
    read: bool = Field(False, index=True)
    count: int = Field(1)  # 合并计数（同 dedup_key 未读重复出现的次数）
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)
