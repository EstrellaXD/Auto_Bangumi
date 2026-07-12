"""Repository for durable rename/revision-replacement operations (#1078)."""

from datetime import datetime, timedelta

from sqlalchemy import delete, or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from module.models.rename_operation import (
    RENAME_OPERATION_STATES,
    RenameOperation,
    RenameOperationState,
    utc_now,
)


def _validate_state(state: str) -> None:
    if state not in RENAME_OPERATION_STATES:
        raise ValueError(f"Unsupported rename operation state: {state}")


class RenameOperationDatabase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, operation_id: int | None) -> RenameOperation | None:
        if operation_id is None:
            return None
        return await self.session.get(RenameOperation, operation_id)

    async def get_by_identity(
        self,
        *,
        downloader_type: str,
        new_task_id: str,
        save_path: str,
        source_path: str,
        target_path: str,
    ) -> RenameOperation | None:
        result = await self.session.execute(
            select(RenameOperation).where(
                RenameOperation.downloader_type == downloader_type,
                RenameOperation.new_task_id == new_task_id,
                RenameOperation.save_path == save_path,
                RenameOperation.source_path == source_path,
                RenameOperation.target_path == target_path,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_target(
        self,
        *,
        downloader_type: str,
        save_path: str,
        target_path: str,
        active_only: bool = True,
    ) -> RenameOperation | None:
        statement = select(RenameOperation).where(
            RenameOperation.downloader_type == downloader_type,
            RenameOperation.save_path == save_path,
            RenameOperation.target_path == target_path,
        )
        if active_only:
            statement = statement.where(RenameOperation.state != "done")
        statement = statement.order_by(  # type: ignore[assignment]
            col(RenameOperation.updated_at).desc()
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_or_create(
        self, operation: RenameOperation
    ) -> tuple[RenameOperation, bool]:
        """Return the identity row, creating it when absent.

        The pre-read handles the normal idempotent path.  The database unique
        indexes remain authoritative for concurrent writers; an identity race
        is re-read after rollback, while an active-target collision is exposed
        as ``IntegrityError`` for the caller to reconcile.
        """

        existing = await self.get_by_identity(
            downloader_type=operation.downloader_type,
            new_task_id=operation.new_task_id,
            save_path=operation.save_path,
            source_path=operation.source_path,
            target_path=operation.target_path,
        )
        if existing is not None:
            return existing, False

        operation.created_at = operation.created_at or utc_now()
        operation.updated_at = utc_now()
        try:
            # Keep an active-target race inside a SAVEPOINT.  Rolling back the
            # whole session would expire unrelated rows already returned to the
            # caller and make a recoverable uniqueness conflict poison the
            # surrounding operation.
            async with self.session.begin_nested():
                self.session.add(operation)
                await self.session.flush()
        except IntegrityError:
            existing = await self.get_by_identity(
                downloader_type=operation.downloader_type,
                new_task_id=operation.new_task_id,
                save_path=operation.save_path,
                source_path=operation.source_path,
                target_path=operation.target_path,
            )
            if existing is not None:
                return existing, False
            raise
        await self.session.commit()
        await self.session.refresh(operation)
        return operation, True

    async def upsert_conflict(
        self, operation: RenameOperation
    ) -> tuple[RenameOperation, bool]:
        """Persist a terminal hold conflict without duplicating notifications."""

        operation.state = "conflict"
        operation.retry_at = None
        existing = await self.get_by_identity(
            downloader_type=operation.downloader_type,
            new_task_id=operation.new_task_id,
            save_path=operation.save_path,
            source_path=operation.source_path,
            target_path=operation.target_path,
        )
        if existing is None:
            return await self.get_or_create(operation)

        # Refresh reconciliation metadata without resetting attempts,
        # notification history, or the original creation timestamp.
        for field_name in (
            "kind",
            "old_task_id",
            "staged_path",
            "bangumi_id",
            "media_type",
            "season",
            "episode",
            "group_name",
            "resolution",
            "old_revision",
            "new_revision",
            "revision_metadata",
            "last_error",
        ):
            setattr(existing, field_name, getattr(operation, field_name))
        existing.state = "conflict"
        existing.retry_at = None
        existing.updated_at = utc_now()
        self.session.add(existing)
        await self.session.commit()
        await self.session.refresh(existing)
        return existing, False

    async def set_state(
        self,
        operation_id: int | None,
        state: RenameOperationState,
        *,
        retry_at: datetime | None = None,
        last_error: str | None = None,
    ) -> RenameOperation | None:
        _validate_state(state)
        row = await self.get(operation_id)
        if row is None:
            return None
        row.state = state
        row.retry_at = retry_at
        row.last_error = last_error
        row.updated_at = utc_now()
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def claim(
        self,
        operation_id: int | None,
        *,
        from_states: tuple[RenameOperationState, ...],
        to_state: RenameOperationState,
        now: datetime | None = None,
    ) -> RenameOperation | None:
        """Atomically claim a due operation and count one execution attempt."""

        if operation_id is None or not from_states:
            return None
        for state in from_states:
            _validate_state(state)
        _validate_state(to_state)
        claimed_at = now or utc_now()
        result = await self.session.execute(
            update(RenameOperation)
            .where(
                col(RenameOperation.id) == operation_id,
                col(RenameOperation.state).in_(from_states),
                or_(
                    col(RenameOperation.retry_at).is_(None),
                    col(RenameOperation.retry_at) <= claimed_at,
                ),
            )
            .values(
                state=to_state,
                attempt_count=RenameOperation.attempt_count + 1,
                retry_at=None,
                updated_at=claimed_at,
            )
            .execution_options(synchronize_session="fetch")
        )
        await self.session.commit()
        if not result.rowcount:  # type: ignore[attr-defined]
            return None
        row = await self.get(operation_id)
        if row is not None:
            await self.session.refresh(row)
        return row

    async def recover_stale_running(
        self, operation_id: int | None, *, before: datetime
    ) -> bool:
        """CAS a crashed ordinary rename lease back to retryable state."""

        if operation_id is None:
            return False
        now = utc_now()
        result = await self.session.execute(
            update(RenameOperation)
            .where(
                col(RenameOperation.id) == operation_id,
                col(RenameOperation.state) == "running",
                col(RenameOperation.updated_at) <= before,
            )
            .values(state="retry", retry_at=None, updated_at=now)
            .execution_options(synchronize_session="fetch")
        )
        await self.session.commit()
        return bool(result.rowcount)  # type: ignore[attr-defined]

    async def claim_replacement_lease(
        self,
        operation_id: int | None,
        *,
        owner: str,
        now: datetime | None = None,
        lease_for: timedelta = timedelta(minutes=5),
    ) -> RenameOperation | None:
        """Fence one replacement Saga across processes for a bounded lease."""

        if operation_id is None:
            return None
        claimed_at = now or utc_now()
        result = await self.session.execute(
            update(RenameOperation)
            .where(
                col(RenameOperation.id) == operation_id,
                col(RenameOperation.kind) == "replacement",
                col(RenameOperation.state).in_(
                    ("planned", "old_staged", "new_promoted", "old_removed")
                ),
                or_(
                    col(RenameOperation.lease_owner).is_(None),
                    col(RenameOperation.lease_expires_at).is_(None),
                    col(RenameOperation.lease_expires_at) <= claimed_at,
                ),
            )
            .values(
                lease_owner=owner,
                lease_expires_at=claimed_at + lease_for,
                attempt_count=RenameOperation.attempt_count + 1,
                updated_at=claimed_at,
            )
            .execution_options(synchronize_session="fetch")
        )
        await self.session.commit()
        if not result.rowcount:  # type: ignore[attr-defined]
            return None
        return await self.get(operation_id)

    async def set_state_claimed(
        self,
        operation_id: int | None,
        *,
        owner: str,
        state: RenameOperationState,
        retry_at: datetime | None = None,
        last_error: str | None = None,
    ) -> RenameOperation | None:
        """Advance a replacement only while the caller still owns its lease."""

        if operation_id is None:
            return None
        _validate_state(state)
        now = utc_now()
        result = await self.session.execute(
            update(RenameOperation)
            .where(
                col(RenameOperation.id) == operation_id,
                col(RenameOperation.lease_owner) == owner,
                col(RenameOperation.lease_expires_at) > now,
            )
            .values(
                state=state,
                retry_at=retry_at,
                last_error=last_error,
                lease_owner=None,
                lease_expires_at=None,
                updated_at=now,
            )
            .execution_options(synchronize_session="fetch")
        )
        await self.session.commit()
        if not result.rowcount:  # type: ignore[attr-defined]
            return None
        return await self.get(operation_id)

    async def release_replacement_lease(
        self, operation_id: int | None, *, owner: str
    ) -> bool:
        if operation_id is None:
            return False
        result = await self.session.execute(
            update(RenameOperation)
            .where(
                col(RenameOperation.id) == operation_id,
                col(RenameOperation.lease_owner) == owner,
            )
            .values(lease_owner=None, lease_expires_at=None, updated_at=utc_now())
            .execution_options(synchronize_session="fetch")
        )
        await self.session.commit()
        return bool(result.rowcount)  # type: ignore[attr-defined]

    async def mark_notified(
        self, operation_id: int | None, when: datetime | None = None
    ) -> bool:
        """Set ``notified_at`` once; concurrent or repeated calls return False."""

        if operation_id is None:
            return False
        notified_at = when or utc_now()
        result = await self.session.execute(
            update(RenameOperation)
            .where(
                col(RenameOperation.id) == operation_id,
                col(RenameOperation.notified_at).is_(None),
            )
            .values(notified_at=notified_at, updated_at=notified_at)
            .execution_options(synchronize_session="fetch")
        )
        await self.session.commit()
        return bool(result.rowcount)  # type: ignore[attr-defined]

    async def list_conflicts(self, limit: int = 100) -> list[RenameOperation]:
        result = await self.session.execute(
            select(RenameOperation)
            .where(RenameOperation.state == "conflict")
            .order_by(col(RenameOperation.updated_at).desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_retryable(
        self, now: datetime | None = None, limit: int = 100
    ) -> list[RenameOperation]:
        ready_at = now or utc_now()
        result = await self.session.execute(
            select(RenameOperation)
            .where(
                RenameOperation.state == "retry",
                or_(
                    col(RenameOperation.retry_at).is_(None),
                    col(RenameOperation.retry_at) <= ready_at,
                ),
            )
            .order_by(col(RenameOperation.retry_at).asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_active_replacements(self, limit: int = 100) -> list[RenameOperation]:
        result = await self.session.execute(
            select(RenameOperation)
            .where(
                RenameOperation.kind == "replacement",
                col(RenameOperation.state).in_(
                    ("planned", "old_staged", "new_promoted", "old_removed")
                ),
            )
            .order_by(col(RenameOperation.updated_at).asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete(self, operation_id: int | None) -> bool:
        row = await self.get(operation_id)
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.commit()
        return True

    async def prune_done(self, before: datetime) -> int:
        result = await self.session.execute(
            delete(RenameOperation)
            .where(
                col(RenameOperation.state) == "done",
                col(RenameOperation.updated_at) < before,
            )
            .execution_options(synchronize_session=False)
        )
        await self.session.commit()
        return int(result.rowcount or 0)  # type: ignore[attr-defined]
