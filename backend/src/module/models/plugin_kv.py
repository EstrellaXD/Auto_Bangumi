"""插件私有键值存储的行。值为 JSON 文本，由 PluginContext.kv 编解码。"""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel, UniqueConstraint


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PluginKV(SQLModel, table=True):
    __tablename__ = "plugin_kv"
    __table_args__ = (UniqueConstraint("plugin_id", "key", name="uq_plugin_kv"),)

    id: int | None = Field(default=None, primary_key=True)
    plugin_id: str = Field(index=True)
    key: str
    value: str
    updated_at: datetime = Field(default_factory=_utcnow)
