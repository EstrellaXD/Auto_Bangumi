"""InboxDatabase — 通知中心消息表的增删查改与合并语义。"""

import json

from sqlmodel import select

from module.database.inbox import InboxDatabase
from module.models import InboxMessage


async def _rows(db_session) -> list[InboxMessage]:
    result = await db_session.execute(select(InboxMessage))
    return list(result.scalars().all())


async def test_upsert_inserts_new_message(db_session):
    db = InboxDatabase(db_session)
    msg = await db.upsert(
        kind="rss_failure",
        severity="error",
        title="RSS 失效",
        body="feed x",
        payload=json.dumps({"rss_url": "http://a/rss"}),
        dedup_key="rss_failure:http://a/rss",
    )
    assert msg is not None
    assert msg.id is not None
    assert msg.count == 1
    assert msg.read is False
    assert len(await _rows(db_session)) == 1


async def test_upsert_unread_same_dedup_coalesces(db_session):
    db = InboxDatabase(db_session)
    first = await db.upsert(
        kind="downloader_unavailable",
        severity="error",
        payload=json.dumps({"reason": "unreachable"}),
        dedup_key="downloader:http://qb:8080",
    )
    # 人为回拨时间戳，验证合并时会刷新 updated_at
    first.updated_at = "2020-01-01T00:00:00+00:00"
    db_session.add(first)
    await db_session.commit()

    second = await db.upsert(
        kind="downloader_unavailable",
        severity="error",
        payload=json.dumps({"reason": "credentials"}),
        dedup_key="downloader:http://qb:8080",
    )

    rows = await _rows(db_session)
    assert len(rows) == 1
    assert second.id == first.id
    assert second.count == 2
    assert json.loads(second.payload)["reason"] == "credentials"  # 最新覆盖
    assert second.updated_at > "2020-01-01T00:00:00+00:00"


async def test_upsert_read_same_dedup_inserts_new_row(db_session):
    db = InboxDatabase(db_session)
    first = await db.upsert(kind="rss_failure", dedup_key="rss:1")
    await db.mark_read(first.id)

    second = await db.upsert(kind="rss_failure", dedup_key="rss:1")

    rows = await _rows(db_session)
    assert len(rows) == 2
    assert second.id != first.id
    assert second.read is False


async def test_upsert_once_skips_when_any_row_exists(db_session):
    db = InboxDatabase(db_session)
    first = await db.upsert(
        kind="update_available", dedup_key="update_available:3.3.1", once=True
    )
    assert first is not None
    await db.mark_read(first.id)

    second = await db.upsert(
        kind="update_available", dedup_key="update_available:3.3.1", once=True
    )

    assert second is None
    assert len(await _rows(db_session)) == 1


async def test_upsert_without_dedup_always_inserts(db_session):
    db = InboxDatabase(db_session)
    await db.upsert(kind="update_applied")
    await db.upsert(kind="update_applied")
    assert len(await _rows(db_session)) == 2


async def test_prune_keeps_newest(db_session):
    db = InboxDatabase(db_session)
    for i in range(5):
        msg = await db.upsert(kind="download_failure")
        msg.updated_at = f"2026-01-0{i + 1}T00:00:00+00:00"
        db_session.add(msg)
    await db_session.commit()

    removed = await db.prune(keep=2)

    assert removed == 3
    rows = await _rows(db_session)
    assert len(rows) == 2
    assert {r.updated_at[:10] for r in rows} == {"2026-01-04", "2026-01-05"}


async def test_upsert_prunes_beyond_keep(db_session):
    db = InboxDatabase(db_session)
    for _ in range(4):
        await db.upsert(kind="download_failure", keep=3)
    assert len(await _rows(db_session)) == 3


async def test_unread_count_and_mark_read(db_session):
    db = InboxDatabase(db_session)
    first = await db.upsert(kind="rss_failure")
    await db.upsert(kind="download_failure")
    assert await db.unread_count() == 2

    assert await db.mark_read(first.id) is True
    assert await db.unread_count() == 1
    assert await db.mark_read(9999) is False


async def test_mark_all_read(db_session):
    db = InboxDatabase(db_session)
    await db.upsert(kind="rss_failure")
    await db.upsert(kind="download_failure")

    changed = await db.mark_all_read()

    assert changed == 2
    assert await db.unread_count() == 0


async def test_delete_and_clear(db_session):
    db = InboxDatabase(db_session)
    first = await db.upsert(kind="rss_failure")
    await db.upsert(kind="download_failure")

    assert await db.delete(first.id) is True
    assert await db.delete(first.id) is False
    assert await db.clear() == 1
    assert len(await _rows(db_session)) == 0


async def test_list_pagination_and_unread_filter(db_session):
    db = InboxDatabase(db_session)
    for i in range(3):
        msg = await db.upsert(kind=f"kind_{i}")
        msg.updated_at = f"2026-01-0{i + 1}T00:00:00+00:00"
        db_session.add(msg)
    await db_session.commit()
    newest = (await db.list(unread_only=False, limit=1, offset=0))[0]
    assert newest.kind == "kind_2"  # updated_at 倒序

    second_page = await db.list(unread_only=False, limit=1, offset=1)
    assert second_page[0].kind == "kind_1"

    await db.mark_read(newest.id)
    unread = await db.list(unread_only=True, limit=10, offset=0)
    assert {m.kind for m in unread} == {"kind_0", "kind_1"}
    assert await db.count_all(unread_only=False) == 3
    assert await db.count_all(unread_only=True) == 2
