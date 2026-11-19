"""宿主服务的故障边界：精确归属、增量完成、持久通知和维护恢复。"""

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from ab_sdk import points
from ab_sdk.library import LibraryFile, OrganizeRequest, OrganizeResult
from module.conf import settings
from module.database import Database
from module.models import Bangumi, Torrent
from module.models.plugin_maintenance import PluginMaintenanceRecord
from module.plugin import host, library, maintenance
from module.plugin.bus import EventBus
from module.plugin.downloads import HostBangumiService, HostDownloadService
from module.plugin.maintenance import HostMaintenanceService
from module.plugin.registry import ProviderEntry
from module.plugin.runner import CircuitBreaker, HookRunner


def bus() -> EventBus:
    result = host.get_bus()
    assert result is not None
    return result


@pytest.fixture
async def application(tmp_path, monkeypatch):
    scheduler = SimpleNamespace(running=True, start_all=Mock())

    async def stop():
        scheduler.running = False

    scheduler.stop_all = AsyncMock(side_effect=stop)
    app = SimpleNamespace(_lifecycle_lock=asyncio.Lock(), scheduler=scheduler)
    monkeypatch.setattr(maintenance, "_application", app)
    monkeypatch.setattr(maintenance, "BACKUP_ROOT", tmp_path / "backups")
    bus = EventBus()
    monkeypatch.setattr(host, "_bus", bus)
    monkeypatch.setattr(library, "_delivered", set())
    yield app
    await bus.close()


async def sample(tmp_path):
    async with Database() as db:
        row = Bangumi(official_title="Example", year="2024", filter="")
        db.add(row)
        await db.commit()
        torrent = Torrent(
            name="Example", qb_hash="task", refer_id=row.id, downloaded=True
        )
        db.add(torrent)
        await db.commit()
    downloads = HostDownloadService()
    task = await downloads.observe(
        "default",
        {"hash": "task", "progress": 0.5, "save_path": "/downloads"},
        [
            {"index": 0, "name": "01.mkv", "size": 3, "progress": 1},
            {"index": 1, "name": "02.mkv", "size": 3, "progress": 0.5},
            {"index": 2, "name": "03.mkv", "size": 3, "progress": 1, "priority": 0},
        ],
    )
    snapshot = await HostBangumiService().get(row.id)
    assert snapshot is not None
    request = OrganizeRequest(task, await downloads.files(task.download_id), snapshot)
    target = tmp_path / "01.mkv"
    target.write_bytes(b"abc")
    return row, torrent, request, target


async def test_committed_targets_validate_scope_completion_and_durable_retry(
    application, tmp_path
):
    _, _, request, target = await sample(tmp_path)
    delivered: list[Any] = []
    fails = True

    async def listener(event):
        nonlocal fails
        delivered.append(event)
        if fails:
            fails = False
            raise RuntimeError("temporary refresh failure")

    bus().subscribe("library.files_committed", listener)
    result = OrganizeResult(
        "operation-1",
        (LibraryFile(request.files.files[0].file_id, str(target), "media"),),
    )
    await library.commit_result("organizer", request, result)
    assert len(delivered) == 1
    await library.replay_commits()
    assert len(delivered) == 2
    assert delivered[-1].files[0].path == str(target)
    await library.commit_result("organizer", request, result)
    assert len(delivered) == 2  # 同一进程已经确认的事件不重复。
    library._delivered.clear()  # 重启后至少一次投递；订阅者按 operation_id 去重。
    await library.replay_commits()
    assert len(delivered) == 3
    history, cursor = await library.HostLibraryService().commits(
        bangumi_id=request.bangumi.id
    )
    assert len(history) == 1 and cursor is None
    for index in [1, 2]:
        bad = replace(
            result,
            operation_id=f"bad-{index}",
            files=(
                replace(result.files[0], file_id=request.files.files[index].file_id),
            ),
        )
        with pytest.raises(ValueError, match="completed task"):
            await library.commit_result("organizer", request, bad)
    with pytest.raises(ValueError, match="completed task"):
        await library.commit_result(
            "organizer",
            request,
            replace(result, files=(replace(result.files[0], file_id="foreign"),)),
        )
    target.write_bytes(b"")
    with pytest.raises(ValueError, match="incomplete"):
        await library.commit_result("organizer", request, result)


async def test_selected_organizer_receives_exact_entry_and_incremental_files(
    application, tmp_path, monkeypatch
):
    _, _, request, _ = await sample(tmp_path)
    monkeypatch.setattr(host, "_registry", None)
    registry = host.get_registry()
    monkeypatch.setattr(host, "_runner", HookRunner(registry, CircuitBreaker()))
    monkeypatch.setattr(settings.plugins.slots, "organizer", "organizer/files")
    from ab_sdk.downloads import RefreshResult

    monkeypatch.setattr(
        HostDownloadService,
        "refresh",
        AsyncMock(return_value=RefreshResult(1, (), (request.task.download_id,))),
    )
    organize = AsyncMock(return_value=None)
    registry.add_provider(
        points.ORGANIZER,
        ProviderEntry("organizer", "files", lambda: SimpleNamespace(organize=organize)),
    )
    await library.organize_selected()
    assert organize.await_count == 1
    assert organize.await_args is not None
    seen = organize.await_args.args[0]
    assert seen.task.bangumi_id == request.bangumi.id
    assert [f.progress for f in seen.files.files] == [1, 0.5, 1]
    # 下载器不可达时不使用持久旧快照启动新的文件操作。
    monkeypatch.setattr(
        HostDownloadService,
        "refresh",
        AsyncMock(return_value=RefreshResult(0, ("default",))),
    )
    await library.organize_selected()
    assert organize.await_count == 1
    registry.remove_plugin("organizer")
    await library.organize_selected()  # 丢失所选插件时无原生回退。


async def test_maintenance_backup_failure_blocks_start_until_explicit_recovery(
    application, tmp_path
):
    service = HostMaintenanceService("demo", tmp_path / "private")
    service.data_dir.mkdir()
    (service.data_dir / "state").write_text("before")

    async def fail(progress):
        assert not application.scheduler.running
        assert (Path(progress.row.backup_path) / "ab.db").is_file()
        assert (
            Path(progress.row.backup_path) / "plugin-data" / "state"
        ).read_text() == "before"
        await progress.checkpoint("writing", {"operation": "test"})
        raise RuntimeError("stop here")

    with pytest.raises(RuntimeError, match="stop here"):
        await service.run("test-failure", fail)
    assert await maintenance.blocked()
    application.scheduler.start_all.assert_not_called()
    [status] = await service.operations()
    assert status.state == "failed" and status.step == "writing"
    with pytest.raises(RuntimeError, match="unfinished"):
        await service.run("another", AsyncMock())
    with pytest.raises(KeyError):
        await HostMaintenanceService("other", tmp_path).status(status.id)
    await service.resume(status.id)
    assert not await maintenance.blocked()
    application.scheduler.start_all.assert_not_called()


async def test_history_preview_exact_one_time_no_media_or_task_deletion(
    application, tmp_path
):
    row, torrent, request, target = await sample(tmp_path)
    service = HostMaintenanceService("review", tmp_path / "private")
    preview = await service.preview_history(row.id, (torrent.id,))
    delivered: list[Any] = []
    bus().subscribe("history.cleared", delivered.append)
    await service.clear_history(preview.token)
    assert target.exists()
    assert await HostDownloadService().files(request.task.download_id)
    async with Database() as db:
        assert await db.session.get(Torrent, torrent.id) is None
    assert delivered[0].release_ids == (torrent.id,)
    assert application.scheduler.start_all.call_count == 1
    with pytest.raises(ValueError, match="consumed"):
        await service.clear_history(preview.token)
    assert not await maintenance.blocked()


async def test_stale_preview_does_not_pause_and_failed_history_notification_is_retried(
    application, tmp_path
):
    row, torrent, _, _ = await sample(tmp_path)
    service = HostMaintenanceService("review", tmp_path / "private")
    preview = await service.preview_history(row.id, (torrent.id,))
    async with Database() as db:
        current = await db.session.get(Bangumi, row.id)
        current.episode_offset = 12
        db.add(current)
        await db.commit()
    with pytest.raises(ValueError, match="expired"):
        await service.clear_history(preview.token)
    application.scheduler.stop_all.assert_not_awaited()
    preview = await service.preview_history(row.id, (torrent.id,))
    unsubscribe = bus().subscribe(
        "history.cleared", Mock(side_effect=RuntimeError("offline"))
    )
    with pytest.raises(RuntimeError, match="listeners"):
        await service.clear_history(preview.token)
    assert await maintenance.blocked()
    unsubscribe()
    retried: list[Any] = []
    bus().subscribe("history.cleared", retried.append)
    operations = [o for o in await service.operations() if o.state == "failed"]
    await service.resume(operations[0].id)
    assert retried[0].operation_id == preview.token
    assert not await maintenance.blocked()


async def test_mapping_event_emitted_after_committed_change(application, tmp_path):
    row, _, _, _ = await sample(tmp_path)
    events: list[Any] = []
    bus().subscribe("bangumi.mapping_changed", events.append)
    async with Database() as db:
        current = await db.bangumi.search_id(row.id)
        current.episode_offset = -12
        await db.bangumi.update(current)
    await bus().drain()
    assert events[-1].old.episode_offset == 0
    assert events[-1].new.episode_offset == -12
    snapshot = await HostBangumiService().get(row.id)
    assert snapshot is not None and snapshot.revision == events[-1].new.revision


async def test_closing_subscriber_completes_queued_confirmation():
    bus = EventBus()
    from ab_sdk.events import HistoryCleared

    entered = asyncio.Event()

    async def wait(event):
        entered.set()
        await asyncio.Event().wait()

    bus.subscribe("history.cleared", wait, owner="slow")
    receipt = asyncio.create_task(
        bus.publish_confirmed(HistoryCleared("x", 1, (), "revision"))
    )
    await entered.wait()
    queued = asyncio.create_task(
        bus.publish_confirmed(HistoryCleared("y", 1, (), "revision"))
    )
    await asyncio.sleep(0)
    await bus.close_owner("slow")
    assert await receipt is False and await queued is False


async def test_maintenance_drains_subscriber_that_attempts_download_without_deadlock(
    application, tmp_path
):
    from ab_sdk.downloader import AddResult
    from ab_sdk.events import HistoryCleared
    from module.plugin.admission import HostAdmissionService

    allowed, entered = asyncio.Event(), asyncio.Event()
    row, _, _, _ = await sample(tmp_path)

    async def listener(event):
        entered.set()
        await allowed.wait()
        # 维护先持久阻止新投递；不能持有 submit 锁等这个订阅者完成。
        assert (
            await HostAdmissionService().submit_with_client(None, None, None)
            is AddResult.HELD
        )

    bus().subscribe("history.cleared", listener)
    bus().publish(HistoryCleared("before-maintenance", row.id, (), "rev"))
    await entered.wait()
    service = HostMaintenanceService("review", tmp_path / "private")
    running = asyncio.create_task(service.run("drain-test", AsyncMock()))
    async with asyncio.timeout(2):
        while not await maintenance.blocked():
            await asyncio.sleep(0)
        allowed.set()
        await running
    assert not await maintenance.blocked()


async def test_cancelled_maintenance_waits_for_backup_thread_before_reporting_failure(
    application, tmp_path, monkeypatch
):
    import threading

    started, release = threading.Event(), threading.Event()

    def backup(destination, db_path, data_dir):
        started.set()
        release.wait(2)
        destination.mkdir(parents=True)
        (destination / "finished").touch()

    monkeypatch.setattr(maintenance, "_backup", backup)
    service = HostMaintenanceService("review", tmp_path / "private")
    operation = asyncio.create_task(service.run("cancel-test", AsyncMock()))
    await asyncio.to_thread(started.wait, 2)
    operation.cancel()
    await asyncio.sleep(0)
    assert not operation.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await operation
    [status] = await service.operations()
    assert status.state == "failed"
    assert list((maintenance.BACKUP_ROOT / "review").glob("*/finished"))
    assert await maintenance.blocked()
    application.scheduler.start_all.assert_not_called()
