"""重命名事务：普通重命名的「同一目标只执行一次」与 V1 → V2 revision 替换 saga。

每一步外部操作（下载器重命名、删除）都先校验、再持久化到 ``rename_operation``
表，进程崩溃后下一轮可以从记录的状态继续推进。由 :class:`Renamer` 继承，
命名策略与编排留在 ``renamer.py``。
"""

import asyncio
import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError

from ab_sdk.rename import FileKind
from module.conf import settings
from module.database import Database
from module.database.bangumi import normalize_save_path
from module.downloader import DownloadClient, RenameOutcome, RenameResult
from module.downloader.path import path_to_bangumi
from module.models import EpisodeFile, Notification, RenameOperation, SubtitleFile
from module.notification import RenameConflictEvent, SystemEvent

from .revision_policy import (
    RevisionIdentity,
    parse_revision_identity,
    replacement_staged_path,
)

logger = logging.getLogger(__name__)

_PENDING_RENAME_COOLDOWN = 300  # 5 minutes cooldown before retrying same rename

# 处理完成标记：供外部脚本（filebot、hlink 等）过滤 AB 已重命名的任务 (#147)。
# 语义 = 顶层媒体文件全部就位；字幕在同一轮循环里紧随其后重命名，深层
# 嵌套文件（特典/花絮）设计上从不重命名——两者都不阻塞打标
_RENAMED_TAG = "ab:renamed"
_replacement_locks: dict[tuple[str, str, str], asyncio.Lock] = {}


@dataclass(frozen=True, slots=True)
class PreparedMediaRename:
    episode: EpisodeFile
    source_path: str
    target_path: str


@dataclass(frozen=True, slots=True)
class MediaRenameReport:
    result: RenameResult
    prepared: PreparedMediaRename | None = None
    notification: Notification | None = None


@dataclass(frozen=True, slots=True)
class RevisionOwner:
    info: dict
    files: list[dict]
    identity: RevisionIdentity | None


class RevisionSaga:
    """由 Renamer 继承；子类提供下载器门面 ``client``、冲突事件列表 ``events``
    与本轮重命名记录 ``_moves``。"""

    client: DownloadClient
    events: list[SystemEvent]
    _moves: dict[str, list[tuple[str, str, FileKind]]]

    def _record_move(self, _hash: str, old: str, new: str, kind: FileKind) -> None:
        """记录一次已生效的重命名，供本轮结束时发布 file.renamed / torrent.organized。"""
        self._moves.setdefault(_hash, []).append((old, new, kind))

    @staticmethod
    def _adjust_episode(original: int | float, episode_offset: int) -> int | float:
        if original == 0 and episode_offset != 0:
            # Episode 0 is a special/OVA — never apply offset to avoid
            # overwriting regular episodes (see issue #977)
            return 0
        adjusted = original + episode_offset
        # An offset producing a non-positive result (e.g., EP5 + offset -10)
        # is almost always a misconfiguration, so revert to original.
        if adjusted < 0 or (adjusted == 0 and original > 0):
            logger.warning(
                f"Episode offset {episode_offset} would make episode {original} non-positive, ignoring offset"
            )
            return original
        return adjusted

    async def _mark_renamed(self, _hash: str, existing_tags: str | None) -> None:
        """给处理完成的种子打 ``ab:renamed`` 标签；已带标签时不再调 API。

        打标失败绝不能影响重命名主流程（重命名已经成功、通知必须发出、
        本轮其余种子必须继续处理）——吞掉异常，下一轮会自动补打。
        """
        if _RENAMED_TAG in (t.strip() for t in (existing_tags or "").split(",")):
            return
        try:
            await self.client.add_tag(_hash, _RENAMED_TAG)
        except Exception as e:
            logger.warning("Failed to tag %s as renamed: %s", _hash[:8], e)

    async def _execute_media_rename(
        self,
        *,
        prepared: PreparedMediaRename,
        bangumi_name: str,
        _hash: str,
        episode_offset: int,
    ) -> MediaRenameReport:
        if prepared.source_path == prepared.target_path:
            return MediaRenameReport(
                result=RenameResult(RenameOutcome.ALREADY_APPLIED),
                prepared=prepared,
            )
        result = await self.client.rename_torrent_file(
            _hash=_hash,
            old_path=prepared.source_path,
            new_path=prepared.target_path,
        )
        notification = None
        if result.outcome is RenameOutcome.RENAMED:
            self._record_move(
                _hash, prepared.source_path, prepared.target_path, "media"
            )
            notification = Notification(
                official_title=bangumi_name,
                season=prepared.episode.season,
                episode=self._adjust_episode(prepared.episode.episode, episode_offset),
            )
        return MediaRenameReport(
            result=result,
            prepared=prepared,
            notification=notification,
        )

    @staticmethod
    def _parse_bangumi_id_from_tags(tags: str | None) -> int | None:
        """Extract bangumi_id from torrent tags.

        Tags are comma-separated, and we look for 'ab:ID' format.
        """
        if not tags:
            return None
        for tag in tags.split(","):
            tag = tag.strip()
            if tag.startswith("ab:"):
                try:
                    return int(tag[3:])
                except ValueError:
                    pass
        return None

    @staticmethod
    def _retry_at() -> datetime:
        return datetime.now(timezone.utc) + timedelta(seconds=_PENDING_RENAME_COOLDOWN)

    @staticmethod
    def _retry_is_due(value: datetime | None) -> bool:
        if value is None:
            return True
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value <= datetime.now(timezone.utc)

    def _downloader_type(self) -> str:
        instance = self.client.instance
        configured = instance.type
        downloader_type = (
            configured
            if isinstance(configured, str)
            else type(self.client.client).__name__.lower()
        )
        host = instance.host
        if not isinstance(host, str) or not host:
            return downloader_type
        instance_hash = hashlib.sha256(host.strip().lower().encode()).hexdigest()[:12]
        return f"{downloader_type}:{instance_hash}"

    async def _find_revision_owners(
        self,
        *,
        incoming: dict,
        target_path: str,
        all_infos: list[dict],
        episode_offset: int,
    ) -> tuple[RevisionIdentity | None, list[RevisionOwner]]:
        """Find downloader tasks that already own an incoming canonical path."""

        incoming_id = self._parse_bangumi_id_from_tags(incoming.get("tags"))
        _, incoming_season = path_to_bangumi(
            incoming.get("save_path", ""),
            incoming.get("name", ""),
            self.client.instance.path,
        )
        incoming_identity = parse_revision_identity(
            incoming.get("name", ""),
            bangumi_id=incoming_id,
            default_season=incoming_season,
            episode_offset=episode_offset,
        )
        if incoming_id is None:
            return incoming_identity, []

        save_path = normalize_save_path(incoming.get("save_path", ""))
        candidates = [
            info
            for info in all_infos
            if info.get("hash") != incoming.get("hash")
            and normalize_save_path(info.get("save_path", "")) == save_path
            and self._parse_bangumi_id_from_tags(info.get("tags")) == incoming_id
        ]
        if not candidates:
            return incoming_identity, []

        candidate_files = await asyncio.gather(
            *[self.client.get_torrent_files(info["hash"]) for info in candidates]
        )
        owners: list[RevisionOwner] = []
        normalized_target = target_path.replace("\\", "/")
        for info, files in zip(candidates, candidate_files):
            # Count every downloader task that references the canonical path
            # before applying the destructive single-file guard. A collection
            # owner must make replacement ineligible, not disappear from the
            # owner count.
            if not any(
                str(item.get("name", "")).replace("\\", "/") == normalized_target
                for item in files
            ):
                continue
            _, old_season = path_to_bangumi(
                info.get("save_path", ""),
                info.get("name", ""),
                self.client.instance.path,
            )
            owners.append(
                RevisionOwner(
                    info=info,
                    files=files,
                    identity=parse_revision_identity(
                        info.get("name", ""),
                        bangumi_id=incoming_id,
                        default_season=old_season,
                        episode_offset=episode_offset,
                    ),
                )
            )
        return incoming_identity, owners

    def _build_operation(
        self,
        *,
        info: dict,
        prepared: PreparedMediaRename,
        identity: RevisionIdentity | None,
        kind: str,
        state: str,
        owner: RevisionOwner | None = None,
        reason: str | None = None,
    ) -> RenameOperation:
        owner_identity = owner.identity if owner else None
        metadata = {
            "new_torrent_name": info.get("name", ""),
            "old_torrent_name": owner.info.get("name", "") if owner else None,
        }
        return RenameOperation(
            downloader_type=self._downloader_type(),
            kind=kind,
            state=state,
            new_task_id=info["hash"],
            old_task_id=owner.info["hash"] if owner else None,
            save_path=normalize_save_path(info.get("save_path", "")),
            source_path=prepared.source_path,
            target_path=prepared.target_path,
            staged_path=(
                replacement_staged_path(
                    prepared.target_path,
                    old_task_id=owner.info["hash"],
                    old_revision=owner_identity.revision,
                )
                if owner and owner_identity
                else None
            ),
            bangumi_id=identity.bangumi_id if identity else None,
            media_type=identity.media_type.value if identity else None,
            season=identity.season if identity else None,
            episode=float(identity.episode) if identity else None,
            group_name=identity.group if identity else None,
            resolution=identity.resolution if identity else None,
            old_revision=owner_identity.revision if owner_identity else None,
            new_revision=identity.revision if identity else None,
            revision_metadata=json.dumps(metadata, ensure_ascii=False),
            last_error=reason,
        )

    async def _emit_conflict_once(
        self,
        operation: RenameOperation,
        *,
        torrent_name: str,
        reason: str,
    ) -> None:
        async with Database() as db:
            claimed = await db.rename_operation.mark_notified(operation.id)
        if claimed:
            self.events.append(
                RenameConflictEvent(
                    task_id=operation.new_task_id,
                    torrent_name=torrent_name,
                    target_path=operation.target_path,
                    reason=reason,
                )
            )

    async def _persist_conflict(
        self,
        *,
        info: dict,
        prepared: PreparedMediaRename,
        identity: RevisionIdentity | None,
        reason: str,
        owner: RevisionOwner | None = None,
    ) -> RenameOperation | None:
        operation = self._build_operation(
            info=info,
            prepared=prepared,
            identity=identity,
            kind="conflict",
            state="conflict",
            owner=owner,
            reason=reason,
        )
        async with Database() as db:
            active = await db.rename_operation.get_by_target(
                downloader_type=operation.downloader_type,
                save_path=operation.save_path,
                target_path=operation.target_path,
            )
            if active is not None and active.new_task_id != operation.new_task_id:
                logger.warning(
                    "Rename target already reserved by task %s: %s",
                    active.new_task_id[:8],
                    operation.target_path,
                )
                return active
            try:
                row, _ = await db.rename_operation.upsert_conflict(operation)
            except IntegrityError:
                row = await db.rename_operation.get_by_target(
                    downloader_type=operation.downloader_type,
                    save_path=operation.save_path,
                    target_path=operation.target_path,
                )
        if row is not None and row.new_task_id == info["hash"]:
            await self._emit_conflict_once(
                row, torrent_name=info.get("name", ""), reason=reason
            )
        return row

    async def _set_operation_state(
        self,
        operation: RenameOperation,
        state: str,
        *,
        retry: bool = False,
        error: str | None = None,
    ) -> RenameOperation:
        async with Database() as db:
            if operation.kind == "replacement" and operation.lease_owner:
                updated = await db.rename_operation.set_state_claimed(
                    operation.id,
                    owner=operation.lease_owner,
                    state=state,  # type: ignore[arg-type]
                    retry_at=self._retry_at() if retry else None,
                    last_error=error,
                )
                if updated is None:
                    raise RuntimeError("replacement lease was lost before state commit")
            else:
                updated = await db.rename_operation.set_state(
                    operation.id,
                    state,  # type: ignore[arg-type]
                    retry_at=self._retry_at() if retry else None,
                    last_error=error,
                )
        return updated or operation

    async def _replacement_conflict(
        self,
        operation: RenameOperation,
        *,
        info: dict,
        reason: str,
    ) -> None:
        operation = await self._set_operation_state(operation, "conflict", error=reason)
        await self._emit_conflict_once(
            operation,
            torrent_name=info.get("name", ""),
            reason=reason,
        )

    async def _advance_replacement(
        self,
        *,
        operation: RenameOperation,
        info: dict,
        prepared: PreparedMediaRename,
        all_infos: list[dict],
        bangumi_name: str,
        episode_offset: int,
        existing_tags: str | None,
    ) -> Notification | None:
        """Advance a staged V1 -> V2 replacement saga as far as possible."""

        key = (
            operation.downloader_type,
            operation.save_path,
            operation.target_path,
        )
        lock = _replacement_locks.setdefault(key, asyncio.Lock())
        async with lock:
            async with Database() as db:
                current = await db.rename_operation.get(operation.id)
            if current is None:
                return None
            operation = current
            if not self._retry_is_due(operation.retry_at):
                return None

            info_by_hash = {item["hash"]: item for item in all_infos}
            staged_path = operation.staged_path
            if not staged_path or not operation.old_task_id:
                await self._replacement_conflict(
                    operation,
                    info=info,
                    reason="replacement operation is missing old owner metadata",
                )
                return None
            old_task_id = operation.old_task_id

            # A bounded loop lets the normal successful path finish in one tick,
            # while every external action is verified and persisted separately.
            for _ in range(6):
                state = operation.state
                if state in {
                    "planned",
                    "old_staged",
                    "new_promoted",
                    "old_removed",
                }:
                    async with Database() as db:
                        claimed = await db.rename_operation.claim_replacement_lease(
                            operation.id,
                            owner=uuid.uuid4().hex,
                        )
                    if claimed is None:
                        return None
                    operation = claimed
                    state = operation.state
                if state == "conflict":
                    await self._emit_conflict_once(
                        operation,
                        torrent_name=info.get("name", ""),
                        reason=operation.last_error or "rename conflict",
                    )
                    return None

                if state == "planned":
                    old_info = info_by_hash.get(old_task_id)
                    if old_info is None:
                        await self._replacement_conflict(
                            operation,
                            info=info,
                            reason="old revision task disappeared before staging",
                        )
                        return None
                    old_files = await self.client.get_torrent_files(old_task_id)
                    old_names = {
                        str(item.get("name", "")).replace("\\", "/")
                        for item in old_files
                    }
                    if staged_path in old_names:
                        operation = await self._set_operation_state(
                            operation, "old_staged"
                        )
                        continue
                    if operation.target_path not in old_names:
                        await self._replacement_conflict(
                            operation,
                            info=info,
                            reason="old revision no longer owns the canonical path",
                        )
                        return None
                    result = await self.client.rename_torrent_file(
                        _hash=old_task_id,
                        old_path=operation.target_path,
                        new_path=staged_path,
                    )
                    if result.succeeded:
                        operation = await self._set_operation_state(
                            operation, "old_staged"
                        )
                        continue
                    if result.outcome is RenameOutcome.DESTINATION_EXISTS:
                        await self._replacement_conflict(
                            operation,
                            info=info,
                            reason="temporary staging path already exists",
                        )
                        return None
                    operation = await self._set_operation_state(
                        operation,
                        "planned",
                        retry=True,
                        error=result.detail or "failed to stage old revision",
                    )
                    return None

                if state == "old_staged":
                    new_files = await self.client.get_torrent_files(
                        operation.new_task_id
                    )
                    new_names = {
                        str(item.get("name", "")).replace("\\", "/")
                        for item in new_files
                    }
                    if operation.target_path in new_names:
                        operation = await self._set_operation_state(
                            operation, "new_promoted"
                        )
                        continue
                    if operation.source_path not in new_names:
                        rollback = await self.client.rename_torrent_file(
                            _hash=old_task_id,
                            old_path=staged_path,
                            new_path=operation.target_path,
                        )
                        if rollback.succeeded:
                            await self._replacement_conflict(
                                operation,
                                info=info,
                                reason=(
                                    "new revision source disappeared after "
                                    "staging; V1 was restored"
                                ),
                            )
                        else:
                            await self._set_operation_state(
                                operation,
                                "old_staged",
                                retry=True,
                                error=(
                                    "new revision source disappeared and V1 "
                                    "rollback needs retry: "
                                    f"{rollback.detail or rollback.outcome.value}"
                                ),
                            )
                        return None
                    result = await self.client.rename_torrent_file(
                        _hash=operation.new_task_id,
                        old_path=operation.source_path,
                        new_path=operation.target_path,
                    )
                    if result.outcome is RenameOutcome.RENAMED:
                        self._record_move(
                            operation.new_task_id,
                            operation.source_path,
                            operation.target_path,
                            "media",
                        )
                    if result.succeeded:
                        operation = await self._set_operation_state(
                            operation, "new_promoted"
                        )
                        continue

                    # Reconcile once more before rollback: a transport failure
                    # may happen after the downloader applied the promotion.
                    new_files = await self.client.get_torrent_files(
                        operation.new_task_id
                    )
                    if any(
                        str(item.get("name", "")).replace("\\", "/")
                        == operation.target_path
                        for item in new_files
                    ):
                        self._record_move(
                            operation.new_task_id,
                            operation.source_path,
                            operation.target_path,
                            "media",
                        )
                        operation = await self._set_operation_state(
                            operation, "new_promoted"
                        )
                        continue

                    rollback = await self.client.rename_torrent_file(
                        _hash=old_task_id,
                        old_path=staged_path,
                        new_path=operation.target_path,
                    )
                    if rollback.succeeded:
                        if result.outcome is RenameOutcome.DESTINATION_EXISTS:
                            await self._replacement_conflict(
                                operation,
                                info=info,
                                reason=(
                                    "V2 promotion target is owned by an unknown "
                                    "file; V1 was restored"
                                ),
                            )
                            return None
                        operation = await self._set_operation_state(
                            operation,
                            "planned",
                            retry=True,
                            error=result.detail
                            or "promotion failed and V1 was restored",
                        )
                        return None
                    if rollback.outcome is RenameOutcome.DESTINATION_EXISTS:
                        await self._replacement_conflict(
                            operation,
                            info=info,
                            reason=(
                                "V2 promotion and V1 rollback both found an "
                                "occupied canonical target"
                            ),
                        )
                        return None
                    operation = await self._set_operation_state(
                        operation,
                        "old_staged",
                        retry=True,
                        error=(
                            "promotion failed and rollback needs retry: "
                            f"{rollback.detail or rollback.outcome.value}"
                        ),
                    )
                    return None

                if state == "new_promoted":
                    old_exists = await self.client.torrent_exists(old_task_id)
                    if old_exists is None:
                        operation = await self._set_operation_state(
                            operation,
                            "new_promoted",
                            retry=True,
                            error=(
                                "new revision is live; old task existence could "
                                "not be verified"
                            ),
                        )
                        return None
                    if old_exists:
                        removed = await self.client.delete_torrent(
                            old_task_id, delete_files=True
                        )
                        if not removed:
                            operation = await self._set_operation_state(
                                operation,
                                "new_promoted",
                                retry=True,
                                error="new revision is live; old task cleanup failed",
                            )
                            return None
                        old_exists = await self.client.torrent_exists(old_task_id)
                        if old_exists is not False:
                            operation = await self._set_operation_state(
                                operation,
                                "new_promoted",
                                retry=True,
                                error=(
                                    "old task deletion was accepted but is not "
                                    "yet observable"
                                ),
                            )
                            return None
                    operation = await self._set_operation_state(
                        operation, "old_removed"
                    )
                    continue

                if state == "old_removed":
                    operation = await self._set_operation_state(operation, "done")
                    continue

                if state == "done":
                    await self._mark_renamed(info["hash"], existing_tags)
                    async with Database() as db:
                        notify = await db.rename_operation.mark_notified(operation.id)
                    if not notify:
                        return None
                    return Notification(
                        official_title=bangumi_name,
                        season=prepared.episode.season,
                        episode=self._adjust_episode(
                            prepared.episode.episode, episode_offset
                        ),
                    )

                # `retry` is only used by ordinary renames. A replacement row
                # reaching it is malformed and must stop rather than guessing.
                await self._replacement_conflict(
                    operation,
                    info=info,
                    reason=f"unexpected replacement state: {state}",
                )
                return None
        return None

    async def _start_replacement(
        self,
        *,
        info: dict,
        prepared: PreparedMediaRename,
        identity: RevisionIdentity,
        owner: RevisionOwner,
        all_infos: list[dict],
        bangumi_name: str,
        episode_offset: int,
        existing_tags: str | None,
    ) -> Notification | None:
        operation = self._build_operation(
            info=info,
            prepared=prepared,
            identity=identity,
            kind="replacement",
            state="planned",
            owner=owner,
        )
        async with Database() as db:
            try:
                row, _ = await db.rename_operation.get_or_create(operation)
            except IntegrityError:
                row = await db.rename_operation.get_by_target(
                    downloader_type=operation.downloader_type,
                    save_path=operation.save_path,
                    target_path=operation.target_path,
                )
        if row is None or row.new_task_id != info["hash"]:
            await self._persist_conflict(
                info=info,
                prepared=prepared,
                identity=identity,
                owner=owner,
                reason="canonical target is reserved by another rename operation",
            )
            return None
        return await self._advance_replacement(
            operation=row,
            info=info,
            prepared=prepared,
            all_infos=all_infos,
            bangumi_name=bangumi_name,
            episode_offset=episode_offset,
            existing_tags=existing_tags,
        )

    async def _recover_missing_replacement(
        self, operation: RenameOperation, all_infos: list[dict]
    ) -> None:
        """Recover an active saga whose incoming task left the normal snapshot."""

        if any(info.get("hash") == operation.new_task_id for info in all_infos):
            return
        async with Database() as db:
            claimed = await db.rename_operation.claim_replacement_lease(
                operation.id,
                owner=uuid.uuid4().hex,
            )
        if claimed is None:
            return
        operation = claimed
        try:
            metadata = json.loads(operation.revision_metadata or "{}")
        except json.JSONDecodeError:
            metadata = {}
        info = {
            "hash": operation.new_task_id,
            "name": metadata.get("new_torrent_name") or operation.new_task_id,
        }
        if operation.state == "old_staged" and operation.old_task_id:
            rollback = await self.client.rename_torrent_file(
                _hash=operation.old_task_id,
                old_path=operation.staged_path or "",
                new_path=operation.target_path,
            )
            if rollback.succeeded:
                await self._replacement_conflict(
                    operation,
                    info=info,
                    reason="incoming revision task disappeared; V1 was restored",
                )
                return
            if rollback.outcome is RenameOutcome.DESTINATION_EXISTS:
                await self._replacement_conflict(
                    operation,
                    info=info,
                    reason=(
                        "incoming revision task disappeared while the canonical "
                        "path remained occupied"
                    ),
                )
                return
            await self._set_operation_state(
                operation,
                "old_staged",
                retry=True,
                error=(
                    "incoming revision task disappeared and V1 rollback needs "
                    f"retry: {rollback.detail or rollback.outcome.value}"
                ),
            )
            return
        if operation.state == "old_removed":
            await self._set_operation_state(operation, "done")
            return
        await self._replacement_conflict(
            operation,
            info=info,
            reason=(
                "incoming revision task disappeared during replacement; "
                "automatic deletion is stopped"
            ),
        )

    async def _run_ordinary_rename(
        self,
        *,
        info: dict,
        prepared: PreparedMediaRename,
        identity: RevisionIdentity | None,
        bangumi_name: str,
        episode_offset: int,
    ) -> MediaRenameReport:
        """Claim and execute one non-replacement rename exactly once at a time."""

        template = self._build_operation(
            info=info,
            prepared=prepared,
            identity=identity,
            kind="conflict",
            state="retry",
        )
        key = (template.downloader_type, template.save_path, template.target_path)
        lock = _replacement_locks.setdefault(key, asyncio.Lock())
        async with lock:
            async with Database() as db:
                active = await db.rename_operation.get_by_target(
                    downloader_type=template.downloader_type,
                    save_path=template.save_path,
                    target_path=template.target_path,
                )
                if active is not None and active.new_task_id != info["hash"]:
                    return MediaRenameReport(
                        result=RenameResult(
                            RenameOutcome.DESTINATION_EXISTS,
                            detail="canonical target is reserved by another operation",
                        ),
                        prepared=prepared,
                    )
                if active is None:
                    try:
                        active, _ = await db.rename_operation.get_or_create(template)
                    except IntegrityError:
                        active = await db.rename_operation.get_by_target(
                            downloader_type=template.downloader_type,
                            save_path=template.save_path,
                            target_path=template.target_path,
                        )
                if active is None:
                    return MediaRenameReport(
                        result=RenameResult(
                            RenameOutcome.RETRYABLE_FAILURE,
                            detail="could not reserve rename operation",
                        ),
                        prepared=prepared,
                    )
                if active.state == "done":
                    return MediaRenameReport(
                        result=RenameResult(RenameOutcome.ALREADY_APPLIED),
                        prepared=prepared,
                    )
                if active.state == "conflict":
                    conflict = active
                    claimed = None
                else:
                    conflict = None
                    if active.state == "running":
                        recovered = await db.rename_operation.recover_stale_running(
                            active.id,
                            before=datetime.now(timezone.utc)
                            - timedelta(seconds=_PENDING_RENAME_COOLDOWN),
                        )
                        if not recovered:
                            return MediaRenameReport(
                                result=RenameResult(
                                    RenameOutcome.RETRYABLE_FAILURE,
                                    detail="rename operation is already running",
                                ),
                                prepared=prepared,
                            )
                        active = await db.rename_operation.get(active.id) or active
                    if active.state == "retry" and not self._retry_is_due(
                        active.retry_at
                    ):
                        return MediaRenameReport(
                            result=RenameResult(
                                RenameOutcome.RETRYABLE_FAILURE,
                                detail=active.last_error or "rename retry cooldown",
                            ),
                            prepared=prepared,
                        )
                    claimed = await db.rename_operation.claim(
                        active.id,
                        from_states=("retry",),
                        to_state="running",
                    )

            if conflict is not None:
                await self._emit_conflict_once(
                    conflict,
                    torrent_name=info.get("name", ""),
                    reason=conflict.last_error or "target already exists",
                )
                return MediaRenameReport(
                    result=RenameResult(
                        RenameOutcome.DESTINATION_EXISTS,
                        detail=conflict.last_error,
                    ),
                    prepared=prepared,
                )
            if claimed is None:
                return MediaRenameReport(
                    result=RenameResult(
                        RenameOutcome.RETRYABLE_FAILURE,
                        detail="rename operation was claimed by another worker",
                    ),
                    prepared=prepared,
                )

            # The downloader may have applied the previous rename just before
            # the process crashed, leaving the DB row in ``running``.  Its own
            # file list is authoritative proof of ownership; reconcile that
            # state before sending the external mutation again (qB commonly
            # answers the replay with 409).
            current_files = await self.client.get_torrent_files(info["hash"])
            current_names = {
                str(item.get("name", "")).replace("\\", "/") for item in current_files
            }
            if (
                prepared.target_path in current_names
                and prepared.source_path not in current_names
            ):
                await self._set_operation_state(claimed, "done")
                return MediaRenameReport(
                    result=RenameResult(RenameOutcome.ALREADY_APPLIED),
                    prepared=prepared,
                )

            report = await self._execute_media_rename(
                prepared=prepared,
                bangumi_name=bangumi_name,
                _hash=info["hash"],
                episode_offset=episode_offset,
            )
            if report.result.succeeded:
                await self._set_operation_state(claimed, "done")
                return report
            if report.result.outcome is RenameOutcome.DESTINATION_EXISTS:
                conflict = await self._set_operation_state(
                    claimed,
                    "conflict",
                    error=report.result.detail or "target path already exists",
                )
                await self._emit_conflict_once(
                    conflict,
                    torrent_name=info.get("name", ""),
                    reason=conflict.last_error or "target path already exists",
                )
                return report
            await self._set_operation_state(
                claimed,
                "retry",
                retry=True,
                error=report.result.detail or "rename failed verification",
            )
            return report
