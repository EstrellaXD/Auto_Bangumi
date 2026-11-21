"""下载快照服务。远端 I/O 与短数据库事务分开，不从标签或标题推断归属。"""

import asyncio
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from sqlmodel import col, select

from ab_sdk.bangumi import BangumiSnapshot
from ab_sdk.downloads import (
    DownloadFile,
    DownloadTask,
    FileSnapshot,
    RefreshResult,
    TaskPage,
)
from module.models.download_task import DownloadTaskRecord


def database():
    from module.database import Database

    return Database()


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def bangumi_snapshot(row) -> BangumiSnapshot:
    values = {
        name: getattr(row, name)
        for name in BangumiSnapshot.__dataclass_fields__
        if name not in {"revision", "effective_season"}
    }
    values["effective_season"] = row.season + row.season_offset
    return BangumiSnapshot(**values, revision=digest(values))


class HostBangumiService:
    async def get(self, bangumi_id: int) -> BangumiSnapshot | None:
        async with database() as db:
            row = await db.bangumi.search_id(bangumi_id)
            return bangumi_snapshot(row) if row else None


def task_snapshot(row: DownloadTaskRecord) -> DownloadTask:
    owners = json.loads(row.bangumi_ids)
    association: Literal["matched", "unmatched", "ambiguous"] = (
        "matched" if len(owners) == 1 else "ambiguous" if owners else "unmatched"
    )
    return DownloadTask(
        row.id,
        row.downloader_id,
        row.provider_task_id,
        owners[0] if len(owners) == 1 else None,
        tuple(json.loads(row.release_ids)),
        association,
        row.name,
        row.save_path,
        row.state,
        row.progress,
        row.revision,
        row.observed_at,
    )


def file_snapshot(download_id: str, files: list[dict], old: list[dict]) -> str:
    originals = {f["index"]: f["original_relative_path"] for f in old}
    result = []
    seen = set()
    for position, raw in enumerate(files):
        index = int(raw.get("index", position))
        name = str(raw["name"]).replace("\\", "/")
        path = PurePosixPath(name)
        if (
            index in seen
            or index < 0
            or path.is_absolute()
            or PureWindowsPath(name).drive
            or ".." in path.parts
            or "\0" in name
        ):
            raise ValueError("Invalid downloader file snapshot")
        seen.add(index)
        size = int(raw.get("size", 0))
        progress = float(raw.get("progress", 0.0))
        if (
            size < 0
            or not math.isfinite(progress)
            or not 0 <= progress <= 1
            or str(path) == "."
        ):
            raise ValueError("Invalid downloader file snapshot")
        result.append(
            {
                "file_id": str(uuid5(NAMESPACE_URL, f"ab:file:{download_id}:{index}")),
                "index": index,
                "relative_path": str(path),
                "original_relative_path": originals.get(index, str(path)),
                "size": size,
                "selected": int(raw.get("priority", 1)) != 0,
                "progress": progress,
            }
        )
    return json.dumps(result, sort_keys=True, ensure_ascii=False)


_refresh_lock = asyncio.Lock()


class HostDownloadService:
    def __init__(self, plugin_id="core"):
        self.plugin_id = plugin_id

    @property
    def _admission(self):
        from .admission import HostAdmissionService

        return HostAdmissionService(self.plugin_id)

    async def policy_revision(self):
        from .admission import policy_revision

        return policy_revision()

    async def submit(self, request, *, idempotency_key, policy_revision):
        return await self._admission.submit(
            request, idempotency_key=idempotency_key, policy_revision=policy_revision
        )

    async def lookup_submission(self, idempotency_key):
        return await self._admission.lookup_submission(idempotency_key)

    async def submissions(self, **kwargs):
        return await self._admission.submissions(**kwargs)

    async def candidates(self, **kwargs):
        return await self._admission.candidates(**kwargs)

    async def recheck_candidates(self, **kwargs):
        return await self._admission.recheck_candidates(**kwargs)

    async def replay(self, candidate_id, **kwargs):
        return await self._admission.replay(candidate_id, **kwargs)

    async def refresh(self) -> RefreshResult:
        from module.downloader import DownloaderPool
        from module.downloader.download_client import downloader_ids

        count, unavailable, observed = 0, [], []
        async with _refresh_lock, DownloaderPool() as pool:
            for instance_id in downloader_ids():
                try:
                    client = await pool.get(instance_id)
                    if not client.client.capabilities.can_query:
                        unavailable.append(instance_id)
                        continue
                    infos = await client.get_torrent_info(status_filter="all")
                    for info in infos:
                        files = await client.get_torrent_files(str(info["hash"]))
                        if not files:
                            # 下载器错误或尚未取得元数据均不覆盖最近可用快照。
                            raise RuntimeError("File snapshot unavailable")
                        task = await self.observe(instance_id, info, files)
                        observed.append(task.download_id)
                        count += 1
                except Exception:
                    # 旧快照仍可查，调用方必须检查 unavailable，不能当作已消失。
                    unavailable.append(instance_id)
        return RefreshResult(count, tuple(unavailable), tuple(observed))

    async def observe(
        self, instance_id: str, info: dict, files: list[dict]
    ) -> DownloadTask:
        from module.models import Torrent
        from module.models.aria2 import Aria2Gid

        task_id = str(info["hash"])
        download_id = str(uuid5(NAMESPACE_URL, f"ab:download:{instance_id}:{task_id}"))
        async with database() as db:
            await db.begin_write()
            row = await db.session.get(DownloadTaskRecord, download_id)
            if row is None:
                row = DownloadTaskRecord(
                    id=download_id, downloader_id=instance_id, provider_task_id=task_id
                )
            owners = set(json.loads(row.bangumi_ids))
            releases = set(json.loads(row.release_ids))
            result = await db.session.execute(
                select(Torrent).where(
                    Torrent.downloader_id == instance_id,
                    Torrent.qb_hash == task_id,
                )
            )
            for torrent in result.scalars():
                releases.add(torrent.id)
                if torrent.bangumi_id is not None:
                    owners.add(torrent.bangumi_id)
            gid = await db.session.get(Aria2Gid, (instance_id, task_id))
            if gid is not None and gid.bangumi_id is not None:
                owners.add(gid.bangumi_id)
            changes = {
                "name": str(info.get("name", "")),
                "save_path": str(info.get("save_path", "")),
                "state": str(info.get("state", "")),
                "progress": float(info.get("progress", 0.0)),
                "bangumi_ids": json.dumps(sorted(owners)),
                "release_ids": json.dumps(sorted(releases)),
                "files": file_snapshot(download_id, files, json.loads(row.files)),
            }
            if any(getattr(row, k) != v for k, v in changes.items()):
                row.revision += 1
            for key, value in changes.items():
                setattr(row, key, value)
            row.observed_at = datetime.now(UTC).isoformat()
            db.add(row)
            await db.commit()
            return task_snapshot(row)

    async def list_tasks(
        self, *, bangumi_id=None, completed=None, cursor=None, limit=100
    ) -> TaskPage:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        query = select(DownloadTaskRecord).order_by(DownloadTaskRecord.id)
        if cursor:
            query = query.where(DownloadTaskRecord.id > cursor)
        if bangumi_id is not None:
            query = query.where(
                DownloadTaskRecord.bangumi_ids == json.dumps([bangumi_id])
            )
        if completed is not None:
            condition = col(DownloadTaskRecord.progress) >= 1.0
            query = query.where(condition if completed else ~condition)
        async with database() as db:
            result = await db.session.execute(query.limit(limit + 1))
            rows = list(result.scalars())
            return TaskPage(
                tuple(task_snapshot(r) for r in rows[:limit]),
                rows[limit - 1].id if len(rows) > limit else None,
            )

    async def files(self, download_id: str) -> FileSnapshot:
        async with database() as db:
            row = await db.session.get(DownloadTaskRecord, download_id)
            if row is None:
                raise KeyError(download_id)
            files = tuple(
                DownloadFile(
                    **f,
                    downloader_path=str(
                        PurePosixPath(row.save_path.replace("\\", "/"))
                        / f["relative_path"]
                    ),
                )
                for f in json.loads(row.files)
            )
            return FileSnapshot(row.id, row.revision, files, row.observed_at)

    async def associate(
        self, download_id: str, bangumi_id: int, *, revision: int
    ) -> DownloadTask:
        async with database() as db:
            await db.begin_write()
            row = await db.session.get(DownloadTaskRecord, download_id)
            if row is None or row.revision != revision:
                raise ValueError("Task snapshot expired")
            if await db.bangumi.search_id(bangumi_id) is None:
                raise ValueError("Unknown bangumi")
            owners = json.loads(row.bangumi_ids)
            if owners and owners != [bangumi_id]:
                raise ValueError("Task already has an association")
            if owners != [bangumi_id]:
                row.bangumi_ids = json.dumps([bangumi_id])
                row.revision += 1
                db.add(row)
                await db.commit()
            return task_snapshot(row)
