"""公共快照契约：归属、稳定身份、部分完成和损坏的远端输入。"""

from dataclasses import FrozenInstanceError

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlmodel import SQLModel

from module.database import Database
from module.database.migrations import (
    create_tables_conn,
    run_migrations_conn,
    set_schema_version,
)
from module.models import Bangumi, Torrent
from module.plugin.downloads import HostBangumiService, HostDownloadService


async def add_bangumi(title="Example"):
    async with Database() as db:
        row = Bangumi(official_title=title, year="2024")
        db.add(row)
        await db.commit()
        return row


def info(task="hash", **kwargs):
    return {
        "hash": task,
        "name": "Example",
        "save_path": "/downloads",
        "progress": 1,
        **kwargs,
    }


def files(name="Example.mkv", progress=1):
    return [{"index": 0, "name": name, "size": 123, "progress": progress}]


async def test_identity_files_and_revisions_survive_service_recreation():
    service = HostDownloadService()
    first = await service.observe("default", info(), files(progress=0.5))
    original = await service.files(first.download_id)
    same = await service.observe("default", info(), files(progress=0.5))
    assert first.download_id == same.download_id and first.revision == same.revision

    restarted = HostDownloadService()
    changed = await restarted.observe("default", info(), files("S01E01.mkv"))
    updated = await restarted.files(first.download_id)
    assert changed.revision > first.revision
    assert original.files[0].file_id == updated.files[0].file_id
    assert updated.files[0].original_relative_path == "Example.mkv"
    assert updated.files[0].downloader_path == "/downloads/S01E01.mkv"
    assert original.files[0].progress == 0.5
    with pytest.raises(FrozenInstanceError):
        changed.name = "mutable"  # type: ignore[misc]


async def test_exact_entry_query_ignores_tags_title_and_shared_library_identity():
    first, second = await add_bangumi(), await add_bangumi()
    async with Database() as db:
        for task, owner in (("first", first.id), ("second", second.id)):
            db.add(Torrent(name="same title", qb_hash=task, refer_id=owner))
        await db.commit()
    service = HostDownloadService()
    one = await service.observe(
        "default", info("first", tags=f"ab:{second.id}"), files()
    )
    await service.observe("default", info("second"), files())
    unknown = await service.observe(
        "other-instance", info("first", tags=f"ab:{first.id}"), files()
    )
    assert unknown.association == "unmatched"
    assert (await service.list_tasks(bangumi_id=first.id)).items == (one,)
    page = await service.list_tasks(limit=1)
    assert len(page.items) == 1 and page.cursor
    rest = await service.list_tasks(cursor=page.cursor, limit=5)
    assert len(rest.items) == 2


async def test_ambiguous_and_manual_associations_cannot_overwrite_ownership():
    one, two = await add_bangumi(), await add_bangumi()
    async with Database() as db:
        for owner in (one.id, two.id):
            db.add(Torrent(qb_hash="ambiguous", refer_id=owner))
        await db.commit()
    service = HostDownloadService()
    ambiguous = await service.observe("default", info("ambiguous"), files())
    assert ambiguous.association == "ambiguous" and ambiguous.bangumi_id is None
    assert not (await service.list_tasks(bangumi_id=one.id)).items
    with pytest.raises(ValueError, match="association"):
        await service.associate(
            ambiguous.download_id, one.id, revision=ambiguous.revision
        )
    unknown = await service.observe("default", info("unknown"), files())
    bound = await service.associate(
        unknown.download_id, one.id, revision=unknown.revision
    )
    assert bound.bangumi_id == one.id
    with pytest.raises(ValueError, match="expired"):
        await service.associate(bound.download_id, two.id, revision=unknown.revision)
    with pytest.raises(ValueError, match="association"):
        await service.associate(bound.download_id, two.id, revision=bound.revision)


@pytest.mark.parametrize("name", ["../escape.mkv", "/absolute.mkv", "C:\\escape.mkv"])
async def test_bad_file_paths_preserve_previous_snapshot(name):
    service = HostDownloadService()
    task = await service.observe("default", info(), files())
    with pytest.raises(ValueError, match="Invalid"):
        await service.observe("default", info(), files(name))
    assert (await service.files(task.download_id)).files[
        0
    ].relative_path == "Example.mkv"


async def test_metadata_snapshot_effective_offsets_and_revision():
    row = await add_bangumi()
    service = HostBangumiService()
    old = await service.get(row.id)
    assert old is not None
    assert old.effective_season == 1
    async with Database() as db:
        current = await db.bangumi.search_id(row.id)
        current.season_offset = 1
        current.episode_offset = -12
        await db.bangumi.update(current)
    new = await service.get(row.id)
    assert new is not None
    assert new.season == 1 and new.effective_season == 2
    assert new.episode_offset == -12 and new.revision != old.revision
    assert await service.get(9999) is None


def test_task_migration_is_repeatable(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'migration.db'}")
    with engine.begin() as conn:
        create_tables_conn(conn)
        conn.execute(text("DROP TABLE download_task"))
        set_schema_version(conn, 28)
        run_migrations_conn(conn)
        run_migrations_conn(conn)
        assert "download_task" in inspect(conn).get_table_names()
