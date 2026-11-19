"""全局独占整理器。未选择插件时仍进入原生流程；选中插件失效则暂停。"""

import asyncio
import json
import stat
from dataclasses import asdict
from pathlib import Path

from sqlmodel import select

from ab_sdk import points
from ab_sdk.events import LibraryFilesCommitted
from ab_sdk.library import LibraryFile, OrganizeRequest, OrganizeResult
from module.conf import settings
from module.models.library_commit import LibraryCommitRecord
from module.plugin import host

from .downloads import HostBangumiService, HostDownloadService, database, digest

organization_lock = asyncio.Lock()
_delivered: set[str] = set()


class HostLibraryService:
    async def selected(self) -> str:
        return settings.plugins.slots.organizer

    async def commits(self, *, bangumi_id=None, cursor=None, limit=100):
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        query = select(LibraryCommitRecord).order_by(LibraryCommitRecord.id)
        if bangumi_id is not None:
            query = query.where(LibraryCommitRecord.bangumi_id == bangumi_id)
        if cursor:
            query = query.where(LibraryCommitRecord.id > cursor)
        async with database() as db:
            rows = list((await db.session.execute(query.limit(limit + 1))).scalars())
            return (
                tuple(json.loads(r.payload) for r in rows[:limit]),
                rows[limit - 1].id if len(rows) > limit else None,
            )


def _verify_files(request: OrganizeRequest, result: OrganizeResult):
    sources = {
        f.file_id: f for f in request.files.files if f.selected and f.progress >= 1
    }
    seen = set()
    if not result.operation_id or not result.files:
        raise ValueError("A committed operation must contain files and an id")
    for target in result.files:
        if target.file_id not in sources or target.file_id in seen:
            raise ValueError("File does not belong to this completed task snapshot")
        seen.add(target.file_id)
        path = Path(target.path)
        if not path.is_absolute() or target.kind not in {
            "media",
            "subtitle",
            "music",
            "archive",
        }:
            raise ValueError("Invalid library file")
        identity = path.stat()
        if (
            not stat.S_ISREG(identity.st_mode)
            or identity.st_size != sources[target.file_id].size
        ):
            raise ValueError("Library target is missing or incomplete")


async def commit_result(plugin_id, request: OrganizeRequest, result: OrganizeResult):
    await asyncio.to_thread(_verify_files, request, result)
    current = await HostBangumiService().get(request.bangumi.id)
    if current is None or current.revision != request.bangumi.revision:
        raise ValueError("Bangumi mapping changed during organization")
    operation_id = digest((plugin_id, result.operation_id))
    event = LibraryFilesCommitted(
        operation_id,
        request.task.download_id,
        request.bangumi.id,
        result.files,
        result.media_identity,
        current.revision,
    )
    payload = json.dumps(asdict(event), ensure_ascii=False, sort_keys=True)
    async with database() as db:
        await db.begin_write()
        row = await db.session.get(LibraryCommitRecord, operation_id)
        if row is not None and row.payload != payload:
            raise ValueError("Operation id reused for different library files")
        if row is None:
            db.add(
                LibraryCommitRecord(
                    id=operation_id,
                    plugin_id=plugin_id,
                    download_id=request.task.download_id,
                    bangumi_id=current.id,
                    payload=payload,
                )
            )
            await db.commit()
    await replay_commits()


async def replay_commits():
    bus = host.get_bus()
    if bus is None:
        return
    async with database() as db:
        rows = list((await db.session.execute(select(LibraryCommitRecord))).scalars())
    for row in rows:
        if row.id in _delivered:
            continue
        values = json.loads(row.payload)
        values["files"] = tuple(LibraryFile(**f) for f in values["files"])
        if await bus.publish_confirmed(LibraryFilesCommitted(**values)):
            _delivered.add(row.id)


async def organize_selected():
    selected = settings.plugins.slots.organizer
    entry = host.get_registry().providers(points.ORGANIZER).get(selected)
    runner = host.get_runner()
    # 选中的插件未登记或熔断，保持独占，不运行原生改名与 hardlink。
    if (
        entry is None
        or runner is None
        or settings.plugins.enabled.get(entry.plugin_id) is False
    ):
        return
    downloads, metadata = HostDownloadService(), HostBangumiService()
    refreshed = await downloads.refresh()
    cursor = None
    while True:
        page = await downloads.list_tasks(cursor=cursor)
        for task in page.items:
            if (
                task.download_id not in refreshed.download_ids
                or task.downloader_id in refreshed.unavailable
                or task.association != "matched"
                or task.bangumi_id is None
            ):
                continue
            bangumi = await metadata.get(task.bangumi_id)
            files = await downloads.files(task.download_id)
            if (
                bangumi is None
                or bangumi.deleted
                or not any(f.selected and f.progress >= 1 for f in files.files)
            ):
                continue
            request = OrganizeRequest(task, files, bangumi)

            async def organize():
                result = await entry.factory().organize(request)
                if result is not None:
                    if not isinstance(result, OrganizeResult):
                        raise TypeError("Invalid organizer result")
                    await commit_result(entry.plugin_id, request, result)

            await runner.call_provider(
                entry.plugin_id,
                points.ORGANIZER,
                organize,
                timeout=3600,
            )
        if page.cursor is None:
            break
        cursor = page.cursor
    await replay_commits()
