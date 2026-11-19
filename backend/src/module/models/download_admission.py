from sqlmodel import Field, SQLModel


class DownloadCandidateRecord(SQLModel, table=True):
    __tablename__ = "download_candidate"

    id: str = Field(primary_key=True)
    batch_id: str = Field(index=True)
    source: str
    payload: str
    bangumi_id: int | None = Field(default=None, index=True)
    stage: str = "unmatched"
    reason: str = ""
    revision: str = ""
    match_ids: str = "[]"
    release: str = "null"


class DownloadSubmissionRecord(SQLModel, table=True):
    __tablename__ = "download_submission"

    id: str = Field(primary_key=True)
    owner: str = Field(index=True)
    idempotency_key: str
    request_urls: str = "[]"
    request_payload: str = "[]"
    fingerprint: str
    policy_revision: str
    mapping_revision: str
    state: str = "pending"
    download_ids: str = "[]"
    provider_task_ids: str = "[]"
    downloader_id: str
    bangumi_id: int
    reason: str = ""
