"""持久准入与投递意图。未知结果只对账，不盲目再次提交。"""

import asyncio
import base64
import json
import re
from collections.abc import Awaitable, Callable
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlmodel import col, select

from ab_sdk import points
from ab_sdk.admission import (
    Admission,
    AdmissionRequest,
    Candidate,
    CandidatePage,
    ReleaseSnapshot,
    Submission,
    SubmissionPage,
    SubmitRequest,
)
from ab_sdk.downloader import AddResult
from ab_sdk.ingest import TorrentInfo
from module.conf import settings
from module.models import Torrent
from module.models.download_admission import (
    DownloadCandidateRecord,
    DownloadSubmissionRecord,
)
from module.models.download_task import DownloadTaskRecord
from module.plugin import host

from .downloads import bangumi_snapshot, database, digest

_submit_lock = asyncio.Lock()
current_batch: ContextVar[str] = ContextVar("download_batch", default="")
before_send: ContextVar[Callable[..., Awaitable[None]] | None] = ContextVar(
    "download_before_send", default=None
)
submission_options: ContextVar[tuple | None] = ContextVar(
    "download_submission_options", default=None
)


@contextmanager
def candidate_batch():
    token = current_batch.set(str(uuid4()))
    try:
        yield current_batch.get()
    finally:
        current_batch.reset(token)


def policy_revision() -> str:
    selected = settings.plugins.slots.download_preflight
    owner = selected.split("/", 1)[0]
    return digest(
        {
            "provider": selected,
            "options": settings.plugins.options.get(owner, {}),
            "enabled": settings.plugins.enabled.get(owner),
            "filter": settings.rss_parser.filter,
        }
    )


def candidate_view(row) -> Candidate:
    return Candidate(
        row.id,
        row.batch_id,
        row.source,
        TorrentInfo(**json.loads(row.payload)),
        row.bangumi_id,
        row.stage,
        row.reason,
        row.revision,
        tuple(json.loads(row.match_ids)),
        ReleaseSnapshot(**json.loads(row.release)) if row.release != "null" else None,
    )


def submission_view(row) -> Submission:
    return Submission(
        row.id,
        row.idempotency_key,
        row.policy_revision,
        row.state,
        tuple(json.loads(row.download_ids)),
        row.reason,
        row.bangumi_id,
        row.owner,
    )


class HostAdmissionService:
    def __init__(self, owner="core"):
        self.owner = owner

    async def capture(
        self,
        torrents,
        *,
        source="native",
        bangumi_id=None,
        stage="unmatched",
        reason="",
        reuse=False,
    ):
        batch_id = current_batch.get() or str(uuid4())
        from module.parser.analyser.selector import parse_configured_release_title
        from module.parser.title_parser import _apply_title_hooks

        parsed_releases = {}
        for torrent in torrents:
            parsed = parse_configured_release_title(torrent.name)
            if parsed is not None:
                parsed = await _apply_title_hooks(parsed)
                parsed_releases[torrent.url] = json.dumps(
                    {
                        name: getattr(parsed, name)
                        for name in ReleaseSnapshot.__dataclass_fields__
                    }
                )
        result = []
        async with database() as db:
            await db.begin_write()
            for torrent in torrents:
                view = TorrentInfo(
                    torrent.name, torrent.url, torrent.homepage, torrent.rss_id
                )
                candidate_id = digest((source, view.url, view.rss_id))
                payload = json.dumps(asdict(view), ensure_ascii=False)
                row = await db.session.get(DownloadCandidateRecord, candidate_id)
                if reuse and row is not None and row.batch_id == batch_id:
                    result.append(candidate_view(row))
                    continue
                if row is None:
                    row = DownloadCandidateRecord(
                        id=candidate_id,
                        batch_id=batch_id,
                        source=source,
                        payload=payload,
                    )
                row.batch_id, row.payload = batch_id, payload
                row.bangumi_id, row.stage, row.reason = bangumi_id, stage, reason
                row.release = parsed_releases.get(view.url, "null")
                row.match_ids = json.dumps([bangumi_id] if bangumi_id else [])
                row.revision = digest(
                    (payload, bangumi_id, stage, reason, row.match_ids, row.release)
                )
                db.add(row)
                result.append(candidate_view(row))
            await db.commit()
        return tuple(result)

    async def candidates(
        self, *, bangumi_id=None, batch_id=None, cursor=None, limit=100
    ):
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        query = select(DownloadCandidateRecord).order_by(DownloadCandidateRecord.id)
        if bangumi_id is not None:
            query = query.where(DownloadCandidateRecord.bangumi_id == bangumi_id)
        if batch_id is not None:
            query = query.where(DownloadCandidateRecord.batch_id == batch_id)
        if cursor:
            query = query.where(DownloadCandidateRecord.id > cursor)
        async with database() as db:
            rows = list((await db.session.execute(query.limit(limit + 1))).scalars())
            return CandidatePage(
                tuple(candidate_view(r) for r in rows[:limit]),
                rows[limit - 1].id if len(rows) > limit else None,
            )

    async def recheck_candidates(self, *, batch_id=None, bangumi_id=None):
        """只重新解析与过滤，绝不下载。全局过滤之前已保存原始候选。"""
        from module.database.bangumi import match_bangumi_in_list
        from module.rss.engine import RSSEngine

        async with database() as db:
            bangumis = await db.bangumi.search_all()
            query = select(DownloadCandidateRecord)
            if batch_id is not None:
                query = query.where(DownloadCandidateRecord.batch_id == batch_id)
            rows = list((await db.session.execute(query)).scalars())
        changes = []
        global_filter = "|".join(settings.rss_parser.filter)
        for row in rows:
            torrent = Torrent(**json.loads(row.payload))
            from module.parser.analyser.selector import parse_configured_release_title
            from module.parser.title_parser import _apply_title_hooks

            parsed = parse_configured_release_title(torrent.name)
            if parsed is not None:
                parsed = await _apply_title_hooks(parsed)
            row.release = json.dumps(
                {
                    name: getattr(parsed, name)
                    for name in ReleaseSnapshot.__dataclass_fields__
                }
                if parsed is not None
                else None
            )
            matches = [
                b
                for b in bangumis
                if match_bangumi_in_list(torrent.name, [b]) is not None
            ]
            if (
                bangumi_id is not None
                and row.bangumi_id != bangumi_id
                and not any(b.id == bangumi_id for b in matches)
            ):
                continue
            row.match_ids = json.dumps(sorted(b.id for b in matches))
            row.bangumi_id = matches[0].id if len(matches) == 1 else None
            if global_filter and re.search(global_filter, torrent.name):
                row.stage, row.reason = "global_filter", "Excluded by global filter"
            elif len(matches) != 1:
                row.stage = "ambiguous" if matches else "unmatched"
                row.reason = (
                    "Multiple matching entries" if matches else "No matching entry"
                )
            elif matches[0].filter and re.search(
                matches[0].filter.replace(",", "|"), torrent.name
            ):
                row.stage, row.reason = "entry_filter", "Excluded by entry filter"
            elif not await RSSEngine.plugin_accepts(torrent, matches[0]):
                row.stage, row.reason = "plugin_filter", "Excluded by torrent.filter"
            else:
                row.stage, row.reason = "matched", "Unique title/season/group match"
            row.revision = digest(
                (
                    row.payload,
                    row.bangumi_id,
                    row.stage,
                    row.reason,
                    row.match_ids,
                    row.release,
                )
            )
            changes.append(row)
        async with database() as db:
            for row in changes:
                db.add(row)
            await db.commit()
        return len(changes)

    async def submissions(self, *, bangumi_id=None, cursor=None, limit=100):
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        query = select(DownloadSubmissionRecord).order_by(DownloadSubmissionRecord.id)
        if bangumi_id is not None:
            query = query.where(DownloadSubmissionRecord.bangumi_id == bangumi_id)
        if cursor:
            query = query.where(DownloadSubmissionRecord.id > cursor)
        async with database() as db:
            rows = list((await db.session.execute(query.limit(limit + 1))).scalars())
        return SubmissionPage(
            tuple(submission_view(r) for r in rows[:limit]),
            rows[limit - 1].id if len(rows) > limit else None,
        )

    async def lookup_submission(self, key):
        submission_id = digest((self.owner, key))
        async with database() as db:
            row = await db.session.get(DownloadSubmissionRecord, submission_id)
        if row is not None and row.state == "unknown":
            row = await self._reconcile(row)
        if row is not None and row.state == "accepted" and row.owner != "core":
            await self._record_releases(row)
        return submission_view(row) if row else None

    async def replay(
        self,
        candidate_id,
        *,
        candidate_revision,
        mapping_revision,
        idempotency_key,
        policy_revision,
    ):
        await self.recheck_candidates()
        async with database() as db:
            row = await db.session.get(DownloadCandidateRecord, candidate_id)
        if row is None or row.revision != candidate_revision:
            raise ValueError("Candidate snapshot expired")
        if row.stage != "matched" or row.bangumi_id is None:
            raise ValueError("Candidate is filtered or has no unique match")
        request = SubmitRequest(
            row.bangumi_id,
            (TorrentInfo(**json.loads(row.payload)),),
            mapping_revision,
            source=row.source,
        )
        token = current_batch.set(row.batch_id)
        try:
            return await self.submit(
                request,
                idempotency_key=idempotency_key,
                policy_revision=policy_revision,
            )
        finally:
            current_batch.reset(token)

    async def _reconcile(self, row):
        from module.downloader import DownloadClient

        ids = json.loads(row.provider_task_ids)
        if not ids:
            return row
        try:
            async with DownloadClient(row.downloader_id) as client:
                present = [await client.torrent_exists(task_id) for task_id in ids]
        except Exception:
            return row
        # 即使此刻查不到，也可能是下载器延迟受理；不能据此重投。
        if all(found is True for found in present):
            async with database() as db:
                current = await db.session.get(DownloadSubmissionRecord, row.id)
                if current is not None and current.state == "unknown":
                    current.state, current.reason = (
                        "accepted",
                        "Confirmed by downloader",
                    )
                    db.add(current)
                    await db.commit()
                    row = current
        return row

    async def submit(
        self, request: SubmitRequest, *, idempotency_key: str, policy_revision: str
    ):
        from module.downloader import DownloadClient, resolve_downloader_id

        if not request.torrents or not idempotency_key:
            raise ValueError("A non-empty request and idempotency key are required")
        async with database() as db:
            bangumi = await db.bangumi.search_id(request.bangumi_id)
            if bangumi is None or bangumi.deleted:
                raise ValueError("Unknown or disabled bangumi")
            if bangumi_snapshot(bangumi).revision != request.mapping_revision:
                raise ValueError("Bangumi snapshot expired")
        torrents = [Torrent(**asdict(t)) for t in request.torrents]
        token = submission_options.set(
            (self.owner, idempotency_key, policy_revision, request.source)
        )
        try:
            async with DownloadClient(
                resolve_downloader_id(request.downloader_id, bangumi.downloader_id)
            ) as client:
                await client.add_torrent(torrents, bangumi)
        finally:
            submission_options.reset(token)
        submission = await self.lookup_submission(idempotency_key)
        if submission is None:
            raise RuntimeError("Submission was not started; maintenance may be active")
        return submission

    async def submit_with_client(self, client, torrents, bangumi):
        from .maintenance import blocked, in_maintenance

        if in_maintenance.get() or await blocked():
            return AddResult.HELD
        original_torrents = torrents
        torrents = torrents if isinstance(torrents, list) else [torrents]
        if not torrents:
            return AddResult.FAILED
        async with database() as db:
            _, generation = await db.plugin_kv.get(
                "core", f"history-generation:{bangumi.id}"
            )
        owner, key, expected, source = submission_options.get() or (
            "core",
            digest(
                (
                    client.instance_id,
                    bangumi.id,
                    generation,
                    sorted(t.url for t in torrents),
                )
            ),
            policy_revision(),
            "rss" if current_batch.get() else "native",
        )
        if expected != policy_revision():
            raise ValueError("Download policy expired")
        fingerprint = digest(
            (client.instance_id, bangumi.id, sorted((t.name, t.url) for t in torrents))
        )
        submission_id = digest((owner, key))
        snapshot = bangumi_snapshot(bangumi)
        async with _submit_lock:
            if await blocked():
                return AddResult.HELD
            async with database() as db:
                row = await db.session.get(DownloadSubmissionRecord, submission_id)
            if row is not None:
                if row.fingerprint != fingerprint:
                    raise ValueError("Idempotency key reused for a different request")
                if row.state == "accepted":
                    return AddResult.DUPLICATE
                if row.state == "unknown":
                    reconciled = await self._reconcile(row)
                    return (
                        AddResult.DUPLICATE
                        if reconciled.state == "accepted"
                        else AddResult.HELD
                    )
            if row is None:
                row = DownloadSubmissionRecord(
                    id=submission_id,
                    owner=owner,
                    idempotency_key=key,
                    fingerprint=fingerprint,
                    request_urls=json.dumps(sorted(t.url for t in torrents)),
                    request_payload=json.dumps(
                        [
                            asdict(TorrentInfo(t.name, t.url, t.homepage, t.rss_id))
                            for t in torrents
                        ]
                    ),
                    policy_revision=expected,
                    mapping_revision=snapshot.revision,
                    downloader_id=client.instance_id,
                    bangumi_id=bangumi.id or 0,
                )
            row.policy_revision, row.mapping_revision = expected, snapshot.revision
            row.state, row.reason = "pending", ""
            async with database() as db:
                unresolved = list(
                    (
                        await db.session.execute(
                            select(DownloadSubmissionRecord).where(
                                DownloadSubmissionRecord.downloader_id
                                == client.instance_id,
                                col(DownloadSubmissionRecord.state).in_(
                                    ["unknown", "pending"]
                                ),
                                DownloadSubmissionRecord.id != row.id,
                            )
                        )
                    ).scalars()
                )
            urls = {t.url for t in torrents}
            if any(
                urls.intersection(json.loads(other.request_urls))
                for other in unresolved
            ):
                row.state, row.reason = (
                    "held",
                    "Another unresolved submission contains this resource",
                )
                await self._save(row)
                return AddResult.HELD
            await self._save(row)
            candidates = await self.capture(
                torrents,
                source=source,
                bangumi_id=bangumi.id,
                stage="matched",
                reuse=True,
            )
            selected = settings.plugins.slots.download_preflight
            if (
                selected
                and source == "rss"
                and any(
                    c.stage != "matched" or c.bangumi_id != bangumi.id
                    for c in candidates
                )
            ):
                row.state, row.reason = (
                    "held",
                    "RSS candidate has no eligible unique match",
                )
                await self._save(row)
                return AddResult.HELD
            if selected:
                entry = (
                    host.get_registry()
                    .providers(points.DOWNLOAD_PREFLIGHT)
                    .get(selected)
                )
                runner = host.get_runner()
                admission = Admission("hold", "Required admission provider unavailable")
                if (
                    entry is not None
                    and runner is not None
                    and settings.plugins.enabled.get(entry.plugin_id) is not False
                ):
                    ok, decision = await runner.call_provider(
                        entry.plugin_id,
                        points.DOWNLOAD_PREFLIGHT,
                        lambda: entry.factory().preflight(
                            AdmissionRequest(
                                row.id,
                                candidates,
                                snapshot,
                                client.instance_id,
                                expected,
                            )
                        ),
                        check=lambda value: (
                            isinstance(value, Admission)
                            and value.decision in {"allow", "hold", "reject"}
                        ),
                    )
                    if ok and isinstance(decision, Admission):
                        admission = decision
                if admission.decision != "allow":
                    row.state = "held" if admission.decision == "hold" else "rejected"
                    row.reason = admission.reason
                    await self._save(row)
                    return AddResult.HELD
            async with database() as db:
                current = await db.bangumi.search_id(bangumi.id)
            if current is not None and (
                current.deleted
                or bangumi_snapshot(current).revision != snapshot.revision
            ):
                row.state, row.reason = (
                    "held",
                    "Bangumi mapping changed during admission",
                )
                await self._save(row)
                return AddResult.HELD
            if expected != policy_revision():
                row.state, row.reason = (
                    "held",
                    "Download policy changed during admission",
                )
                await self._save(row)
                return AddResult.HELD

            async def starting(urls, payloads):
                # 在远端可能产生副作用之前持久化 unknown，即使进程被杀也不重投。
                ids = self._provider_ids(client, urls, payloads)
                row.provider_task_ids = json.dumps(ids)
                await self._bind_tasks(row, torrents)
                row.state, row.reason = "unknown", "Awaiting downloader result"
                await self._save(row)

            token = before_send.set(starting)
            try:
                result = await client._add_torrent_direct(original_torrents, bangumi)
            except ValueError:
                if row.state == "pending":
                    row.state, row.reason = "held", "Task association requires review"
                    await self._save(row)
                    return AddResult.HELD
                raise
            finally:
                before_send.reset(token)
            if result in {AddResult.ADDED, AddResult.DUPLICATE}:
                row.state, row.reason = "accepted", "Downloader accepted request"
            elif row.state == "pending":
                row.state, row.reason = "failed", "Failed before downloader submission"
            await self._save(row)
            return result

    @staticmethod
    def _provider_ids(client, urls, payloads):
        if client.instance.type != "qbittorrent":
            return []
        from module.downloader.client.qb_downloader import _torrent_infohash

        ids = []
        for url in urls if isinstance(urls, list) else [urls] if urls else []:
            match = re.search(r"xt=urn:btih:([0-9a-fA-F]{40}|[A-Za-z2-7]{32})", url)
            if match:
                value = match.group(1)
                ids.append(
                    base64.b32decode(value.upper()).hex()
                    if len(value) == 32
                    else value.lower()
                )
        for payload in (
            payloads if isinstance(payloads, list) else [payloads] if payloads else []
        ):
            value = _torrent_infohash(payload)
            if value:
                ids.append(value)
        return ids

    @staticmethod
    async def _bind_tasks(row, torrents):
        task_ids = json.loads(row.provider_task_ids)
        if len(task_ids) != len(torrents):
            return
        download_ids = []
        async with database() as db:
            await db.begin_write()
            for task_id, torrent in zip(task_ids, torrents):
                download_id = str(
                    uuid5(NAMESPACE_URL, f"ab:download:{row.downloader_id}:{task_id}")
                )
                task = await db.session.get(DownloadTaskRecord, download_id)
                if task is None:
                    task = DownloadTaskRecord(
                        id=download_id,
                        downloader_id=row.downloader_id,
                        provider_task_id=task_id,
                    )
                owners = set(json.loads(task.bangumi_ids))
                # 明确归属不能被另一个条目的重复添加覆盖。
                if owners and owners != {row.bangumi_id}:
                    raise ValueError("Downloader task belongs to another entry")
                if row.bangumi_id:
                    owners.add(row.bangumi_id)
                task.bangumi_ids = json.dumps(sorted(owners))
                db.add(task)
                torrent.qb_hash = task_id
                download_ids.append(download_id)
            await db.commit()
        row.download_ids = json.dumps(download_ids)

    @staticmethod
    async def _record_releases(row):
        """SDK 投递也进入原生历史；按条目和 URL 更新，不复制已有种子行。"""
        payload = json.loads(row.request_payload)
        ids = json.loads(row.provider_task_ids)
        async with database() as db:
            await db.begin_write()
            for index, item in enumerate(payload):
                existing = (
                    (
                        await db.session.execute(
                            select(Torrent).where(
                                Torrent.bangumi_id == row.bangumi_id,
                                Torrent.url == item["url"],
                            )
                        )
                    )
                    .scalars()
                    .first()
                )
                torrent = existing if existing is not None else Torrent(**item)
                torrent.bangumi_id = row.bangumi_id
                torrent.downloader_id = row.downloader_id
                torrent.downloaded = True
                if len(ids) == len(payload):
                    torrent.qb_hash = ids[index]
                db.add(torrent)
            await db.commit()

    @staticmethod
    async def _save(row):
        async with database() as db:
            db.add(row)
            await db.commit()
