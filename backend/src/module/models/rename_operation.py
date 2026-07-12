"""Durable rename/revision-replacement operation state (#1078).

Downloader calls deliberately happen outside database transactions.  This row
is the small, durable state machine that lets a later rename pass reconcile the
observable downloader state and continue an idempotent operation after a retry
or process restart.
"""

from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import CheckConstraint, Index, text
from sqlmodel import Field, SQLModel

RenameOperationState = Literal[
    "conflict",
    "retry",
    "running",
    "planned",
    "old_staged",
    "new_promoted",
    "old_removed",
    "done",
]

RENAME_OPERATION_STATES: tuple[str, ...] = (
    "conflict",
    "retry",
    "running",
    "planned",
    "old_staged",
    "new_promoted",
    "old_removed",
    "done",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RenameOperation(SQLModel, table=True):
    """One conflict or recoverable revision-replacement operation.

    The full identity prevents duplicate rows for one downloader task/path
    request.  A partial unique index separately reserves an active canonical
    target; completed history is excluded so a later V3 operation is not
    blocked by an older V2 row.
    """

    __tablename__ = "rename_operation"
    __table_args__ = (
        CheckConstraint(
            "state IN ('conflict', 'retry', 'running', 'planned', 'old_staged', "
            "'new_promoted', 'old_removed', 'done')",
            name="ck_rename_operation_state",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_rename_operation_attempt_count",
        ),
        Index(
            "ux_rename_operation_identity",
            "downloader_type",
            "new_task_id",
            "save_path",
            "source_path",
            "target_path",
            unique=True,
        ),
        Index(
            "ux_rename_operation_active_target",
            "downloader_type",
            "save_path",
            "target_path",
            unique=True,
            sqlite_where=text("state NOT IN ('done')"),
            postgresql_where=text("state NOT IN ('done')"),
        ),
        Index("ix_rename_operation_state_retry_at", "state", "retry_at"),
        Index("ix_rename_operation_new_task_id", "new_task_id"),
        Index("ix_rename_operation_old_task_id", "old_task_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    downloader_type: str = Field(max_length=32)
    kind: str = Field(default="conflict", max_length=32)
    state: str = Field(default="planned", max_length=32)

    # Downloader task ownership.  A hold conflict may not have a resolved old
    # owner yet; every operation always has the incoming/new task id.
    new_task_id: str
    old_task_id: str | None = None

    # All paths are downloader-relative except save_path, which is the
    # normalized task root.  staged_path is deterministic for crash recovery.
    save_path: str
    source_path: str
    target_path: str
    staged_path: str | None = None

    # Parsed content identity and revision snapshot used to revalidate a
    # replacement after restart.  revision_metadata stores the lossless JSON
    # snapshot/raw titles for fields that do not warrant schema columns.
    bangumi_id: int | None = None
    media_type: str | None = Field(default=None, max_length=32)
    season: int | None = None
    episode: float | None = None
    group_name: str | None = None
    resolution: str | None = Field(default=None, max_length=32)
    old_revision: int | None = None
    new_revision: int | None = None
    revision_metadata: str | None = None

    attempt_count: int = 0
    retry_at: datetime | None = None
    lease_owner: str | None = Field(default=None, max_length=64)
    lease_expires_at: datetime | None = None
    notified_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
