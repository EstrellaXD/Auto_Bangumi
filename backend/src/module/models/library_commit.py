from sqlmodel import Field, SQLModel


class LibraryCommitRecord(SQLModel, table=True):
    __tablename__ = "library_commit"

    id: str = Field(primary_key=True)
    plugin_id: str
    download_id: str = Field(index=True)
    bangumi_id: int = Field(index=True)
    payload: str
