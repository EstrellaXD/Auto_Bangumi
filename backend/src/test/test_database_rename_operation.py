"""RenameOperationDatabase — #1078 durable rename/replacement state."""

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from module.database import Database
from module.database.rename_operation import RenameOperationDatabase
from module.models import RenameOperation


def _operation(**overrides) -> RenameOperation:
    values: dict[str, Any] = {
        "downloader_type": "qbittorrent",
        "kind": "replacement",
        "state": "planned",
        "new_task_id": "new-v2",
        "old_task_id": "old-v1",
        "save_path": "/downloads/Anime/Season 1",
        "source_path": "[ANi] Anime - 01 [V2].mp4",
        "target_path": "Anime S01E01.mp4",
        "staged_path": ".ab-replace/old-v1/Anime S01E01.mp4",
        "bangumi_id": 42,
        "media_type": "episode",
        "season": 1,
        "episode": 1.0,
        "group_name": "ANi",
        "resolution": "1080p",
        "old_revision": 1,
        "new_revision": 2,
        "revision_metadata": '{"old":"V1","new":"V2"}',
    }
    values.update(overrides)
    return RenameOperation(**values)


async def test_get_or_create_persists_complete_operation_metadata(db_session):
    repo = RenameOperationDatabase(db_session)

    row, created = await repo.get_or_create(_operation())

    assert created is True
    assert row.id is not None
    assert row.old_task_id == "old-v1"
    assert row.staged_path == ".ab-replace/old-v1/Anime S01E01.mp4"
    assert row.old_revision == 1
    assert row.new_revision == 2
    assert row.revision_metadata == '{"old":"V1","new":"V2"}'
    assert row.attempt_count == 0
    assert row.created_at is not None
    assert row.updated_at is not None

    same, duplicate_created = await repo.get_or_create(_operation())
    assert duplicate_created is False
    assert same.id == row.id
    assert await repo.get(row.id) == row


async def test_active_target_is_unique_but_done_history_does_not_block_v3(db_session):
    repo = RenameOperationDatabase(db_session)
    first, _ = await repo.get_or_create(_operation(state="conflict"))

    with pytest.raises(IntegrityError):
        await repo.get_or_create(
            _operation(
                new_task_id="new-v3",
                source_path="[ANi] Anime - 01 [V3].mp4",
                new_revision=3,
            )
        )

    await repo.set_state(first.id, "done")
    v3, created = await repo.get_or_create(
        _operation(
            new_task_id="new-v3",
            source_path="[ANi] Anime - 01 [V3].mp4",
            new_revision=3,
        )
    )
    assert created is True
    assert v3.new_revision == 3


async def test_upsert_conflict_is_idempotent_and_refreshes_error(db_session):
    repo = RenameOperationDatabase(db_session)

    first, created = await repo.upsert_conflict(
        _operation(state="retry", last_error="qB 409")
    )
    assert created is True
    assert first.state == "conflict"
    assert first.retry_at is None

    same, created_again = await repo.upsert_conflict(
        _operation(
            state="planned",
            old_task_id="resolved-old-owner",
            last_error="destination still exists",
        )
    )
    assert created_again is False
    assert same.id == first.id
    assert same.state == "conflict"
    assert same.old_task_id == "resolved-old-owner"
    assert same.last_error == "destination still exists"


async def test_claim_is_atomic_due_only_and_increments_attempt(db_session):
    repo = RenameOperationDatabase(db_session)
    now = datetime.now(timezone.utc)
    row, _ = await repo.get_or_create(
        _operation(state="retry", retry_at=now - timedelta(seconds=1))
    )

    claimed = await repo.claim(
        row.id,
        from_states=("retry",),
        to_state="planned",
        now=now,
    )

    assert claimed is not None
    assert claimed.state == "planned"
    assert claimed.attempt_count == 1
    assert claimed.retry_at is None
    assert (
        await repo.claim(
            row.id,
            from_states=("retry",),
            to_state="planned",
            now=now,
        )
        is None
    )

    future, _ = await repo.get_or_create(
        _operation(
            new_task_id="future-v3",
            source_path="future-v3.mkv",
            target_path="Anime S01E02.mp4",
            state="retry",
            retry_at=now + timedelta(hours=1),
        )
    )
    assert (
        await repo.claim(
            future.id,
            from_states=("retry",),
            to_state="planned",
            now=now,
        )
        is None
    )


async def test_mark_notified_is_one_shot(db_session):
    repo = RenameOperationDatabase(db_session)
    row, _ = await repo.upsert_conflict(_operation())
    notified_at = datetime.now(timezone.utc)

    assert await repo.mark_notified(row.id, notified_at) is True
    assert await repo.mark_notified(row.id, notified_at + timedelta(seconds=1)) is False

    loaded = await repo.get(row.id)
    assert loaded is not None
    assert loaded.notified_at == notified_at


async def test_recover_stale_running_uses_compare_and_swap(db_session):
    repo = RenameOperationDatabase(db_session)
    now = datetime.now(timezone.utc)
    row, _ = await repo.get_or_create(_operation(state="running"))
    row.updated_at = now - timedelta(minutes=10)
    db_session.add(row)
    await db_session.commit()

    assert await repo.recover_stale_running(row.id, before=now - timedelta(minutes=5))
    assert not await repo.recover_stale_running(
        row.id, before=now - timedelta(minutes=5)
    )
    loaded = await repo.get(row.id)
    assert loaded is not None
    assert loaded.state == "retry"


async def test_replacement_phase_lease_fences_workers_and_state_commit(db_session):
    repo = RenameOperationDatabase(db_session)
    now = datetime.now(timezone.utc)
    row, _ = await repo.get_or_create(_operation())

    first = await repo.claim_replacement_lease(row.id, owner="worker-a", now=now)
    second = await repo.claim_replacement_lease(row.id, owner="worker-b", now=now)

    assert first is not None
    assert first.lease_owner == "worker-a"
    assert first.attempt_count == 1
    assert second is None
    assert (
        await repo.set_state_claimed(row.id, owner="worker-b", state="old_staged")
        is None
    )

    advanced = await repo.set_state_claimed(
        row.id, owner="worker-a", state="old_staged"
    )
    assert advanced is not None
    assert advanced.state == "old_staged"
    assert advanced.lease_owner is None
    assert advanced.lease_expires_at is None


async def test_expired_replacement_phase_lease_can_be_reclaimed(db_session):
    repo = RenameOperationDatabase(db_session)
    now = datetime.now(timezone.utc)
    row, _ = await repo.get_or_create(_operation())
    assert await repo.claim_replacement_lease(
        row.id,
        owner="crashed-worker",
        now=now - timedelta(minutes=10),
        lease_for=timedelta(minutes=5),
    )

    reclaimed = await repo.claim_replacement_lease(
        row.id, owner="recovery-worker", now=now
    )

    assert reclaimed is not None
    assert reclaimed.lease_owner == "recovery-worker"
    assert reclaimed.attempt_count == 2


async def test_conflict_query_and_done_pruning(db_session):
    repo = RenameOperationDatabase(db_session)
    now = datetime.now(timezone.utc)
    await repo.get_or_create(
        _operation(state="retry", retry_at=now - timedelta(seconds=1))
    )
    await repo.get_or_create(
        _operation(
            new_task_id="later-v3",
            source_path="later-v3.mkv",
            target_path="Anime S01E02.mp4",
            state="retry",
            retry_at=now + timedelta(hours=1),
        )
    )
    conflict, _ = await repo.upsert_conflict(
        _operation(
            new_task_id="conflict-v4",
            source_path="conflict-v4.mkv",
            target_path="Anime S01E03.mp4",
        )
    )

    assert [row.id for row in await repo.list_conflicts()] == [conflict.id]

    await repo.set_state(conflict.id, "done")
    conflict.updated_at = now - timedelta(days=31)
    db_session.add(conflict)
    await db_session.commit()
    assert (
        await repo.prune_done(
            before=now - timedelta(days=30),
            live_task_ids={"conflict-v4"},
            downloader_type=None,
        )
        == 1
    )


@pytest.mark.parametrize(
    ("live_task_ids", "downloader_type", "pruned"),
    [
        ({"new-v2"}, None, False),
        ({"other-task"}, None, True),
        (set(), None, False),
        ({"other-task"}, "qbittorrent", True),
        ({"other-task"}, "aria2", False),
    ],
    ids=[
        "task-present",
        "task-gone",
        "empty-snapshot",
        "same-instance",
        "other-instance",
    ],
)
async def test_prune_done_unchanged_path_rows_only_when_task_gone(
    db_session, live_task_ids, downloader_type, pruned
):
    """路径未变（重命名方式 none）的 done 记录是只通知一次的依据：任务仍在、
    快照为空或属于别的实例时保留，任务已从该实例删除时清理（#1082）。"""
    repo = RenameOperationDatabase(db_session)
    now = datetime.now(timezone.utc)
    row, _ = await repo.get_or_create(
        _operation(
            kind="conflict",
            state="done",
            source_path="Anime - 01.mkv",
            target_path="Anime - 01.mkv",
        )
    )
    row.updated_at = now - timedelta(days=31)
    db_session.add(row)
    await db_session.commit()

    assert await repo.prune_done(
        before=now - timedelta(days=30),
        live_task_ids=live_task_ids,
        downloader_type=downloader_type,
    ) == int(pruned)
    db_session.expunge_all()
    assert (await repo.get(row.id) is None) is pruned


async def test_database_facade_exposes_rename_operation_repository(db_engine):
    async with Database(engine=db_engine) as db:
        row, created = await db.rename_operation.get_or_create(_operation())
        assert created is True
        assert await db.rename_operation.get(row.id) is not None


async def test_get_by_target_active_filter_uses_partial_unique_index(db_session):
    """state 过滤必须写成 NOT IN ('done')，才能命中同样条件的部分唯一索引。"""
    repo = RenameOperationDatabase(db_session)
    captured: list[Any] = []
    original = db_session.execute

    async def spy(statement, *args, **kwargs):
        captured.append(statement)
        return await original(statement, *args, **kwargs)

    db_session.execute = spy  # type: ignore[method-assign]
    await repo.get_by_target(
        downloader_type="qbittorrent", save_path="/d", target_path="t.mp4"
    )
    db_session.execute = original  # type: ignore[method-assign]

    plan = await db_session.execute(
        text(
            "EXPLAIN QUERY PLAN "
            + str(captured[0].compile(compile_kwargs={"literal_binds": True}))
        )
    )
    assert "ux_rename_operation_active_target" in " ".join(r[3] for r in plan)
