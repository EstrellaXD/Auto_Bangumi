"""进程内互斥 + 持久维护状态。失败后保持暂停，直到显式恢复。"""

import asyncio
import json
import re
import shutil
import sqlite3
import time
from contextvars import ContextVar
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from sqlmodel import col, select

from ab_sdk.events import HistoryCleared
from ab_sdk.maintenance import HistoryPreview, LegacyOutput, MaintenanceStatus
from module.conf import settings
from module.models import Torrent
from module.models.download_admission import DownloadSubmissionRecord
from module.models.plugin_kv import PluginKV
from module.models.plugin_maintenance import PluginMaintenanceRecord
from module.plugin import host

from .admission import _submit_lock, policy_revision
from .downloads import HostBangumiService, database, digest
from .library import organization_lock

_application = None
_lock = asyncio.Lock()
_history_lock = asyncio.Lock()
in_maintenance: ContextVar[bool] = ContextVar("in_plugin_maintenance", default=False)
BACKUP_ROOT = Path("config/plugin-backups")


async def run_io(function, *args, **kwargs):
    """取消请求也先等待当前文件操作结束，避免后台线程继续修改备份。"""
    task = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        await task
        raise


def configure(application):
    global _application
    _application = application


async def blocked() -> bool:
    async with database() as db:
        query = select(PluginMaintenanceRecord.id).where(
            col(PluginMaintenanceRecord.state).in_(["running", "failed"])
        )
        return (await db.session.execute(query.limit(1))).first() is not None


def _backup(destination: Path, db_path: str, data_dir: Path):
    from module.conf.config import CONFIG_PATH

    destination.mkdir(parents=True, mode=0o700)
    with (
        sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as source,
        sqlite3.connect(destination / "ab.db") as target,
    ):
        source.backup(target)
    if data_dir.exists():
        shutil.copytree(data_dir, destination / "plugin-data", symlinks=True)
    config = CONFIG_PATH
    if config.is_file():
        shutil.copy2(config, destination / "config.json")


class Progress:
    def __init__(self, row):
        self.row = row

    async def checkpoint(self, step: str, details: dict | None = None):
        self.row.step = step
        if details is not None:
            self.row.payload = json.dumps(details, ensure_ascii=False)
        async with database() as db:
            db.add(self.row)
            await db.commit()


class HostMaintenanceService:
    def __init__(self, owner: str, data_dir: Path):
        self.owner, self.data_dir = owner, data_dir

    async def operations(self):
        async with database() as db:
            rows = list(
                (
                    await db.session.execute(
                        select(PluginMaintenanceRecord).where(
                            PluginMaintenanceRecord.owner == self.owner,
                            PluginMaintenanceRecord.state != "preview",
                        )
                    )
                ).scalars()
            )
        return tuple(
            MaintenanceStatus(r.id, r.name, r.state, r.step, r.backup_path, r.error)
            for r in rows
        )

    async def run(self, name, operation):
        if in_maintenance.get() or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", name):
            raise ValueError("Invalid or nested maintenance operation")
        application = _application
        if application is None:
            raise RuntimeError("Maintenance requires a running application")
        current = asyncio.current_task()
        if current is not None and current.get_name().startswith(
            ("periodic:", "event-subscriber:")
        ):
            raise RuntimeError(
                "Run maintenance from an API action, not a scheduled task"
            )
        async with _lock, application._lifecycle_lock:
            if await blocked():
                raise RuntimeError(
                    "An unfinished maintenance operation requires recovery"
                )
            was_running = application.scheduler.running
            await application.scheduler.stop_all()
            row = PluginMaintenanceRecord(id=str(uuid4()), owner=self.owner, name=name)
            progress = Progress(row)
            token = in_maintenance.set(True)
            try:
                # 先持久阻止新投递，再 drain；不能持有投递锁等待可能投递的订阅者。
                await progress.checkpoint("quiescing", {"was_running": was_running})
                bus = host.get_bus()
                if bus is not None:
                    await bus.drain()
                async with _submit_lock, organization_lock:
                    await progress.checkpoint("backup")
                    async with database() as db:
                        db_path = db.session.get_bind().url.database
                    destination = BACKUP_ROOT / self.owner / row.id
                    await run_io(_backup, destination, db_path, self.data_dir)
                    row.backup_path = str(destination)
                    await progress.checkpoint("running", {"was_running": was_running})
                    result = await operation(progress)
                    row.state = "complete"
                    await progress.checkpoint("complete")
            except BaseException as error:
                row.state, row.error = "failed", type(error).__name__
                await progress.checkpoint(row.step)
                raise
            finally:
                in_maintenance.reset(token)
            if was_running:
                application.scheduler.start_all()
            return result

    async def status(self, operation_id):
        async with database() as db:
            row = await db.session.get(PluginMaintenanceRecord, operation_id)
        if row is None or row.owner != self.owner:
            raise KeyError(operation_id)
        return MaintenanceStatus(
            row.id, row.name, row.state, row.step, row.backup_path, row.error
        )

    async def resume(self, operation_id):
        application = _application
        if application is None:
            raise RuntimeError("Maintenance requires a running application")
        async with _lock, application._lifecycle_lock:
            async with database() as db:
                row = await db.session.get(PluginMaintenanceRecord, operation_id)
            if (
                row is None
                or row.owner != self.owner
                or row.state not in {"failed", "running"}
            ):
                raise ValueError("No interrupted operation to acknowledge")
            if row.name == "local-plugin-update" and row.step in {
                "replacing-code",
                "loaded",
            }:
                raise ValueError("Use updates.recover to restore interrupted code")
            if row.name == "clear-history":
                preview_id = json.loads(row.payload).get("preview")
                if preview_id:
                    async with database() as db:
                        preview = await db.session.get(
                            PluginMaintenanceRecord, preview_id
                        )
                    if preview is not None and preview.state == "consumed":
                        payload = json.loads(preview.payload)
                        bus = host.get_bus()
                        if bus is not None and not await bus.publish_confirmed(
                            HistoryCleared(
                                preview_id,
                                payload["bangumi_id"],
                                tuple(payload["release_ids"]),
                                payload["revision"],
                            )
                        ):
                            raise RuntimeError(
                                "History listeners still require recovery"
                            )
            row.state = "acknowledged"
            async with database() as db:
                db.add(row)
                await db.commit()
        # 解除阻断不自动开启程序，用户仍通过原生开始按钮恢复。

    async def _history(self, bangumi_id, release_ids):
        async with database() as db:
            bangumi = await db.bangumi.search_id(bangumi_id)
            if bangumi is None:
                raise ValueError("Unknown bangumi")
            unknown = (
                await db.session.execute(
                    select(DownloadSubmissionRecord.id).where(
                        DownloadSubmissionRecord.bangumi_id == bangumi_id,
                        col(DownloadSubmissionRecord.state).in_(["unknown", "pending"]),
                    )
                )
            ).first()
            if unknown is not None:
                raise ValueError("Unresolved submission prevents history clearing")
            rows = list(
                (
                    await db.session.execute(
                        select(Torrent)
                        .where(
                            Torrent.bangumi_id == bangumi_id,
                            col(Torrent.id).in_(release_ids),
                        )
                        .order_by(col(Torrent.id))
                    )
                ).scalars()
            )
        if {r.id for r in rows} != set(release_ids):
            raise ValueError("History selection expired or belongs to another entry")
        snapshot = await HostBangumiService().get(bangumi_id)
        if snapshot is None:
            raise ValueError("Bangumi changed during history preview")
        revision = digest(
            ([r.model_dump() for r in rows], snapshot.revision, policy_revision())
        )
        return rows, revision

    async def preview_history(self, bangumi_id, release_ids):
        if not release_ids:
            raise ValueError("Select exact release ids")
        rows, revision = await self._history(bangumi_id, release_ids)
        token = str(uuid4())
        async with database() as db:
            db.add(
                PluginMaintenanceRecord(
                    id=token,
                    owner=self.owner,
                    name="history-preview",
                    state="preview",
                    payload=json.dumps(
                        {
                            "bangumi_id": bangumi_id,
                            "release_ids": release_ids,
                            "revision": revision,
                            "expires": time.time() + 900,
                        }
                    ),
                )
            )
            await db.commit()
        return HistoryPreview(
            token, bangumi_id, tuple((r.id, r.name) for r in rows), revision
        )

    async def clear_history(self, token):
        async with _history_lock:
            await self._clear_history(token)

    async def _clear_history(self, token):
        async with database() as db:
            preview = await db.session.get(PluginMaintenanceRecord, token)
        if preview is None or preview.owner != self.owner or preview.state != "preview":
            raise ValueError("Invalid or consumed preview")
        payload = json.loads(preview.payload)
        if time.time() > payload["expires"]:
            raise ValueError("History preview expired")
        _, revision = await self._history(payload["bangumi_id"], payload["release_ids"])
        if revision != payload["revision"]:
            raise ValueError("History preview expired")

        async def clear(progress):
            if time.time() > payload["expires"]:
                raise ValueError("History preview expired")
            rows, revision = await self._history(
                payload["bangumi_id"], payload["release_ids"]
            )
            if revision != payload["revision"]:
                raise ValueError("History preview expired")
            await progress.checkpoint("clearing-history", {"preview": token})
            async with database() as db:
                await db.begin_write()
                from .downloads import bangumi_snapshot

                bangumi = await db.bangumi.search_id(payload["bangumi_id"])
                if (
                    bangumi is None
                    or digest(
                        (
                            [r.model_dump() for r in rows],
                            bangumi_snapshot(bangumi).revision,
                            policy_revision(),
                        )
                    )
                    != revision
                ):
                    raise ValueError("History preview expired")
                # 只删除预览中的宿主历史，不操作媒体、qB 或下载关联表。
                for row in rows:
                    current = await db.session.get(Torrent, row.id)
                    if current is None or current.model_dump() != row.model_dump():
                        raise ValueError("History changed after preview")
                    await db.session.delete(current)
                preview.state = "consumed"
                db.add(preview)
                bangumi = await db.bangumi.search_id(payload["bangumi_id"])
                bangumi.eps_collect = False
                db.add(bangumi)
                await db.plugin_kv.set(
                    "core", f"history-generation:{payload['bangumi_id']}", token
                )
                await db.commit()
            await progress.checkpoint("notifying-history-clear", {"preview": token})
            bus = host.get_bus()
            if bus is not None and not await bus.publish_confirmed(
                HistoryCleared(
                    token,
                    payload["bangumi_id"],
                    tuple(payload["release_ids"]),
                    revision,
                )
            ):
                raise RuntimeError("History listeners require recovery")

        await self.run("clear-history", clear)

    async def legacy_outputs(self, source_identity, *, work_scope):
        root = Path(work_scope)
        if (
            not root.is_absolute()
            or ".." in root.parts
            or len(root.parts) < 3
            or len(source_identity) != 4
        ):
            raise ValueError(
                "An explicit work directory and source stat identity are required"
            )
        async with database() as db:
            rows = list(
                (
                    await db.session.execute(
                        select(PluginKV).where(
                            PluginKV.plugin_id == "hardlink",
                            col(PluginKV.key).startswith("link:"),
                        )
                    )
                ).scalars()
            )
        result = []
        for row in rows:
            path = Path(row.key.removeprefix("link:"))
            if not path.is_relative_to(root):
                continue
            record = json.loads(row.value)
            if (
                isinstance(record, list)
                and len(record) == 2
                and tuple(record[0]) == tuple(source_identity)
            ):
                result.append(
                    LegacyOutput(
                        str(path),
                        tuple(record[0]),
                        tuple(record[1]),
                        settings.plugins.slots.rename_strategy,
                    )
                )
        return tuple(result)
