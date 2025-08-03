from datetime import datetime

from sqlmodel import Field, SQLModel


class DatabaseVersion(SQLModel, table=True):
    """数据库版本记录表"""

    id: int = Field(default=None, primary_key=True)
    version: str = Field(index=True, title="数据库版本")
    applied_at: datetime = Field(default_factory=datetime.utcnow, title="应用时间")
    description: str = Field(default="", title="版本描述")
