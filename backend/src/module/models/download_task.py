"""任务身份与文件快照独立于下载器标签保存。"""

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class DownloadTaskRecord(SQLModel, table=True):
    __tablename__ = "download_task"
    __table_args__ = (UniqueConstraint("downloader_id", "provider_task_id"),)

    id: str = Field(primary_key=True)
    downloader_id: str = Field(index=True)
    provider_task_id: str
    bangumi_ids: str = "[]"
    release_ids: str = "[]"
    name: str = ""
    save_path: str = ""
    state: str = ""
    progress: float = 0.0
    revision: int = 1
    observed_at: str = ""
    files: str = "[]"
