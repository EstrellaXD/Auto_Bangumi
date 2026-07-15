import asyncio
import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import PurePath

from sqlalchemy.exc import IntegrityError

from module.conf import settings
from module.database import Database
from module.database.bangumi import (
    build_save_path_index,
    match_bangumi_in_list,
    normalize_save_path,
)
from module.downloader import DownloadClient, RenameOutcome, RenameResult
from module.downloader.path import check_files, is_ep, path_to_bangumi
from module.models import EpisodeFile, Notification, RenameOperation, SubtitleFile
from module.notification import RenameConflictEvent
from module.parser import TitleParser

from .revision_policy import (
    RevisionIdentity,
    is_strict_upgrade,
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


class Renamer:
    def __init__(self, client: DownloadClient):
        self.client = client
        self._parser = TitleParser()
        self._offset_cache: dict[str, tuple[int, int]] = {}
        self.events: list[RenameConflictEvent] = []

    @staticmethod
    def print_result(torrent_count, rename_count):
        if rename_count != 0:
            logger.info(
                f"Finished checking {torrent_count} files' name, renamed {rename_count} files."
            )
        logger.debug("Checked %s files", torrent_count)

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

    @staticmethod
    def _format_episode(episode: int | float) -> str:
        # 总集篇等半集（12.5）保留小数，否则会覆盖同季的整数集 (#667)；
        # 整数值沿用两位补零
        if isinstance(episode, float) and episode.is_integer():
            episode = int(episode)
        return f"0{episode}" if episode < 10 else str(episode)

    @staticmethod
    def gen_movie_path(
        file_info: EpisodeFile | SubtitleFile,
        movie_name: str,
        method: str,
    ) -> str:
        if method in ("none", "subtitle_none"):
            return file_info.media_path
        return f"{movie_name}{file_info.suffix}"

    @staticmethod
    def gen_path(
        file_info: EpisodeFile | SubtitleFile,
        bangumi_name: str,
        method: str,
        episode_offset: int = 0,
        season_offset: int = 0,  # Kept for API compatibility, but no longer used
    ) -> str:
        # Season comes from the folder name which already includes the offset
        # (folder is now "Season {season + season_offset}")
        # So we use file_info.season directly without applying offset again
        season_num = file_info.season
        season = f"0{season_num}" if season_num < 10 else season_num
        episode = Renamer._format_episode(
            Renamer._adjust_episode(file_info.episode, episode_offset)
        )
        # 注意：group_tag 只影响 qB RSS 规则名（downloader/path.py 的 rule_name），
        # 从不写进重命名后的文件名——已有做种媒体库的文件名必须保持稳定，
        # 否则升级后会触发整库批量重命名，破坏 Plex/Jellyfin 索引与硬链接
        if method == "none" or method == "subtitle_none":
            return file_info.media_path
        # 注意：这里的 title/bangumi_name 来自已存在于磁盘上的文件/文件夹名
        # （单个路径分量，不可能含分隔符），不做保留字符清洗——追加清洗会让
        # 既有做种库（如含 ":" 的标题）在升级后被整库批量重命名 (#721 评审)
        title = file_info.title
        if file_info.episode_type == "movie":
            # 电影/剧场版：Title (Year).ext，不使用 SxxExx 编号。bangumi_name 由
            # 调用方传入，与 gen_save_path 的文件夹命名保持一致 (Title (Year))
            base = bangumi_name if "advance" in method else title
            if method.startswith("subtitle_"):
                assert isinstance(
                    file_info, SubtitleFile
                ), "subtitle methods require a SubtitleFile"
                return f"{base}.{file_info.language}{file_info.suffix}"
            return f"{base}{file_info.suffix}"
        elif method == "pn":
            return f"{title} S{season}E{episode}{file_info.suffix}"
        elif method == "advance":
            return f"{bangumi_name} S{season}E{episode}{file_info.suffix}"
        elif method == "normal":
            logger.warning("Normal rename method is deprecated.")
            return file_info.media_path
        elif method == "subtitle_pn":
            assert isinstance(
                file_info, SubtitleFile
            ), "subtitle_pn requires a SubtitleFile"
            return f"{title} S{season}E{episode}.{file_info.language}{file_info.suffix}"
        elif method == "subtitle_advance":
            assert isinstance(
                file_info, SubtitleFile
            ), "subtitle_advance requires a SubtitleFile"
            return f"{bangumi_name} S{season}E{episode}.{file_info.language}{file_info.suffix}"
        else:
            logger.error(f"Unknown rename method: {method}")
            return file_info.media_path

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

    async def rename_file(
        self,
        torrent_name: str,
        media_path: str,
        bangumi_name: str,
        method: str,
        season: int,
        _hash: str,
        episode_offset: int = 0,
        season_offset: int = 0,
        episode_type: str = "episode",
        existing_tags: str | None = None,
        **kwargs,
    ):
        report = await self._rename_media_file(
            torrent_name=torrent_name,
            media_path=media_path,
            bangumi_name=bangumi_name,
            method=method,
            season=season,
            _hash=_hash,
            episode_offset=episode_offset,
            season_offset=season_offset,
            episode_type=episode_type,
        )
        if report.result.succeeded and method not in ("none", "normal"):
            await self._mark_renamed(_hash, existing_tags)
        return report.notification

    def _prepare_media_rename(
        self,
        *,
        torrent_name: str,
        media_path: str,
        bangumi_name: str,
        method: str,
        season: int,
        episode_offset: int = 0,
        season_offset: int = 0,
        episode_type: str = "episode",
    ) -> PreparedMediaRename | None:
        ep = self._parser.torrent_parser(
            torrent_name=torrent_name,
            torrent_path=media_path,
            season=season,
            episode_type=episode_type,
        )
        if ep is None:
            return None
        return PreparedMediaRename(
            episode=ep,
            source_path=media_path,
            target_path=self.gen_path(
                ep,
                bangumi_name,
                method=method,
                episode_offset=episode_offset,
                season_offset=season_offset,
            ),
        )

    async def _execute_media_rename(
        self,
        *,
        prepared: PreparedMediaRename,
        bangumi_name: str,
        _hash: str,
        episode_offset: int,
        notify_if_unchanged: bool = False,
    ) -> MediaRenameReport:
        if prepared.source_path == prepared.target_path:
            notification = None
            if notify_if_unchanged:
                notification = Notification(
                    official_title=bangumi_name,
                    season=prepared.episode.season,
                    episode=self._adjust_episode(
                        prepared.episode.episode, episode_offset
                    ),
                )
            return MediaRenameReport(
                result=RenameResult(RenameOutcome.ALREADY_APPLIED),
                prepared=prepared,
                notification=notification,
            )
        result = await self.client.rename_torrent_file(
            _hash=_hash,
            old_path=prepared.source_path,
            new_path=prepared.target_path,
        )
        notification = None
        if result.outcome is RenameOutcome.RENAMED:
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

    async def _rename_media_file(
        self,
        *,
        torrent_name: str,
        media_path: str,
        bangumi_name: str,
        method: str,
        season: int,
        _hash: str,
        episode_offset: int = 0,
        season_offset: int = 0,
        episode_type: str = "episode",
    ) -> MediaRenameReport:
        prepared = self._prepare_media_rename(
            torrent_name=torrent_name,
            media_path=media_path,
            bangumi_name=bangumi_name,
            method=method,
            season=season,
            episode_offset=episode_offset,
            season_offset=season_offset,
            episode_type=episode_type,
        )
        if prepared is None:
            logger.warning("%s parse failed", media_path)
            if settings.bangumi_manage.remove_bad_torrent:
                await self.client.delete_torrent(hashes=_hash)
            return MediaRenameReport(
                result=RenameResult(
                    RenameOutcome.RETRYABLE_FAILURE,
                    detail="media path could not be parsed",
                )
            )
        return await self._execute_media_rename(
            prepared=prepared,
            bangumi_name=bangumi_name,
            _hash=_hash,
            episode_offset=episode_offset,
            notify_if_unchanged=method == "none",
        )

    @staticmethod
    def _gen_movie_extra_path(new_path: str, media_path: str) -> str:
        """多文件电影种子中，非主文件在干净名（Title (Year).ext）基础上追加
        原始文件名词干作区分，避免与主文件生成相同目标名互相冲突/覆盖；
        词干若已带 "Title (Year) - " 前缀则先剥离，保证重命名幂等。"""
        suffix = PurePath(new_path).suffix
        base = new_path[: -len(suffix)] if suffix else new_path
        stem = PurePath(media_path).stem
        prefix = f"{base} - "
        if stem.startswith(prefix):
            stem = stem[len(prefix) :]
        return f"{base} - {stem}{suffix}"

    async def rename_movie_file(
        self,
        torrent_name: str,
        media_path: str,
        movie_name: str,
        method: str,
        _hash: str,
        **kwargs,
    ):
        ep = self._parser.torrent_parser(
            torrent_name=torrent_name,
            torrent_path=media_path,
            episode_type="movie",
        )
        if ep:
            new_path = self.gen_movie_path(ep, movie_name, method=method)
            if media_path != new_path:
                if await self.client.rename_torrent_file(
                    _hash=_hash, old_path=media_path, new_path=new_path
                ):
                    return Notification(
                        official_title=movie_name,
                        season=0,
                        episode=0,
                    )
        else:
            logger.warning(f"{media_path} parse failed (movie)")
        return None

    async def rename_collection(
        self,
        media_list: list[str],
        bangumi_name: str,
        season: int,
        method: str,
        _hash: str,
        episode_offset: int = 0,
        season_offset: int = 0,
        episode_type: str = "episode",
        file_sizes: dict[str, int] | None = None,
        existing_tags: str | None = None,
        mark_complete: bool = True,
        torrent_info: dict | None = None,
        **kwargs,
    ):
        # 多文件电影种子（正片 + 特典/花絮）：所有文件会解析出同一标题，
        # 需选出主文件（体积最大者，无体积信息时取首个），其余文件追加区分词干
        movie_primary: str | None = None
        if episode_type == "movie":
            ep_list = [p for p in media_list if is_ep(p)]
            if ep_list:
                if file_sizes:
                    movie_primary = max(ep_list, key=lambda p: file_sizes.get(p, 0))
                else:
                    movie_primary = ep_list[0]
        all_renamed = True
        for media_path in media_list:
            if is_ep(media_path):
                ep = self._parser.torrent_parser(
                    torrent_path=media_path,
                    season=season,
                    episode_type=episode_type,
                )
                if ep:
                    new_path = self.gen_path(
                        ep,
                        bangumi_name,
                        method=method,
                        episode_offset=episode_offset,
                        season_offset=season_offset,
                    )
                    if (
                        movie_primary is not None
                        and media_path != movie_primary
                        and new_path != media_path
                    ):
                        # new_path == media_path 说明是 none 等直通方法，不做区分
                        new_path = self._gen_movie_extra_path(new_path, media_path)
                    if media_path != new_path:
                        prepared = PreparedMediaRename(
                            episode=ep,
                            source_path=media_path,
                            target_path=new_path,
                        )
                        if torrent_info is not None:
                            identity = parse_revision_identity(
                                torrent_info.get("name", ""),
                                bangumi_id=self._parse_bangumi_id_from_tags(
                                    torrent_info.get("tags")
                                ),
                                default_season=season,
                                episode_offset=episode_offset,
                            )
                            report = await self._run_ordinary_rename(
                                info=torrent_info,
                                prepared=prepared,
                                identity=identity,
                                bangumi_name=bangumi_name,
                                episode_offset=episode_offset,
                            )
                            result = report.result
                        else:
                            result = await self.client.rename_torrent_file(
                                _hash=_hash,
                                old_path=media_path,
                                new_path=new_path,
                            )
                        if not result.succeeded:
                            all_renamed = False
                            logger.warning(f"{media_path} rename failed")
                else:
                    # 解析失败的媒体文件不会被重命名——不能算处理完成
                    all_renamed = False
        if all_renamed and mark_complete and method not in ("none", "normal"):
            await self._mark_renamed(_hash, existing_tags)
        return all_renamed

    async def rename_subtitles(
        self,
        subtitle_list: list[str],
        torrent_name: str,
        bangumi_name: str,
        season: int,
        method: str,
        _hash,
        episode_offset: int = 0,
        season_offset: int = 0,
        episode_type: str = "episode",
        **kwargs,
    ):
        method = "subtitle_" + method
        for subtitle_path in subtitle_list:
            sub = self._parser.torrent_parser(
                torrent_path=subtitle_path,
                torrent_name=torrent_name,
                season=season,
                file_type="subtitle",
                episode_type=episode_type,
            )
            if sub:
                new_path = self.gen_path(
                    sub,
                    bangumi_name,
                    method=method,
                    episode_offset=episode_offset,
                    season_offset=season_offset,
                )
                if subtitle_path != new_path:
                    # Skip verification for subtitles to reduce latency
                    renamed = await self.client.rename_torrent_file(
                        _hash=_hash,
                        old_path=subtitle_path,
                        new_path=new_path,
                        verify=False,
                    )
                    if not renamed:
                        logger.warning(f"{subtitle_path} rename failed")

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
    def _has_tag(tags: str | None, expected: str) -> bool:
        return expected in (tag.strip() for tag in (tags or "").split(","))

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
        configured = settings.downloader.type
        downloader_type = (
            configured
            if isinstance(configured, str)
            else type(self.client.client).__name__.lower()
        )
        host = settings.downloader.host
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
            incoming.get("save_path", ""), incoming.get("name", "")
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
                info.get("save_path", ""), info.get("name", "")
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
        notify_if_unchanged: bool = False,
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
                notify_if_unchanged=notify_if_unchanged,
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

    async def _process_single_torrent(
        self,
        *,
        info: dict,
        files: list[dict],
        media_path: str,
        all_infos: list[dict],
        bangumi_name: str,
        season: int,
        method: str,
        episode_offset: int,
        season_offset: int,
        episode_type: str,
    ) -> MediaRenameReport:
        prepared = self._prepare_media_rename(
            torrent_name=info["name"],
            media_path=media_path,
            bangumi_name=bangumi_name,
            method=method,
            season=season,
            episode_offset=episode_offset,
            season_offset=season_offset,
            episode_type=episode_type,
        )
        if prepared is None:
            logger.warning("%s parse failed", media_path)
            if settings.bangumi_manage.remove_bad_torrent:
                await self.client.delete_torrent(hashes=info["hash"])
            return MediaRenameReport(
                result=RenameResult(
                    RenameOutcome.RETRYABLE_FAILURE,
                    detail="media path could not be parsed",
                )
            )

        incoming_id = self._parse_bangumi_id_from_tags(info.get("tags"))
        identity = parse_revision_identity(
            info.get("name", ""),
            bangumi_id=incoming_id,
            default_season=season,
            episode_offset=episode_offset,
        )
        save_path = normalize_save_path(info.get("save_path", ""))
        async with Database() as db:
            active = await db.rename_operation.get_by_target(
                downloader_type=self._downloader_type(),
                save_path=save_path,
                target_path=prepared.target_path,
            )

        if active is not None:
            if active.new_task_id != info["hash"]:
                return MediaRenameReport(
                    result=RenameResult(
                        RenameOutcome.DESTINATION_EXISTS,
                        detail="canonical target is reserved by another operation",
                    ),
                    prepared=prepared,
                )
            if active.state == "conflict":
                await self._emit_conflict_once(
                    active,
                    torrent_name=info.get("name", ""),
                    reason=active.last_error or "target already exists",
                )
                return MediaRenameReport(
                    result=RenameResult(
                        RenameOutcome.DESTINATION_EXISTS,
                        detail=active.last_error,
                    ),
                    prepared=prepared,
                )
            if active.kind == "replacement" and active.state != "done":
                notification = await self._advance_replacement(
                    operation=active,
                    info=info,
                    prepared=prepared,
                    all_infos=all_infos,
                    bangumi_name=bangumi_name,
                    episode_offset=episode_offset,
                    existing_tags=info.get("tags"),
                )
                async with Database() as db:
                    refreshed = await db.rename_operation.get(active.id)
                finished = refreshed is not None and refreshed.state == "done"
                return MediaRenameReport(
                    result=RenameResult(
                        (
                            RenameOutcome.RENAMED
                            if finished
                            else RenameOutcome.RETRYABLE_FAILURE
                        ),
                        detail=(
                            None
                            if finished
                            else (refreshed.last_error if refreshed else None)
                        ),
                    ),
                    prepared=prepared,
                    notification=notification,
                )
            if active.state == "retry" and not self._retry_is_due(active.retry_at):
                return MediaRenameReport(
                    result=RenameResult(
                        RenameOutcome.RETRYABLE_FAILURE,
                        detail=active.last_error or "rename retry cooldown",
                    ),
                    prepared=prepared,
                )
            if active.state == "done":
                return MediaRenameReport(
                    result=RenameResult(RenameOutcome.ALREADY_APPLIED),
                    prepared=prepared,
                )

        incoming_identity, owners = await self._find_revision_owners(
            incoming=info,
            target_path=prepared.target_path,
            all_infos=all_infos,
            episode_offset=episode_offset,
        )
        if owners:
            owner = owners[0] if len(owners) == 1 else None
            reason = "canonical path has more than one downloader owner"
            can_replace = bool(
                owner is not None
                and len(files) == 1
                and len(owner.files) == 1
                and incoming_identity is not None
                and owner.identity is not None
                and is_strict_upgrade(owner.identity, incoming_identity)
            )
            if (
                settings.bangumi_manage.revision_conflict_policy == "replace"
                and can_replace
            ):
                assert owner is not None
                assert incoming_identity is not None
                notification = await self._start_replacement(
                    info=info,
                    prepared=prepared,
                    identity=incoming_identity,
                    owner=owner,
                    all_infos=all_infos,
                    bangumi_name=bangumi_name,
                    episode_offset=episode_offset,
                    existing_tags=info.get("tags"),
                )
                async with Database() as db:
                    replacement = await db.rename_operation.get_by_target(
                        downloader_type=self._downloader_type(),
                        save_path=save_path,
                        target_path=prepared.target_path,
                    )
                finished = replacement is not None and replacement.state == "done"
                return MediaRenameReport(
                    result=RenameResult(
                        (
                            RenameOutcome.RENAMED
                            if finished
                            else RenameOutcome.RETRYABLE_FAILURE
                        ),
                        detail=(replacement.last_error if replacement else None),
                    ),
                    prepared=prepared,
                    notification=notification,
                )

            if len(owners) == 1:
                assert owner is not None
                if len(files) != 1 or len(owner.files) != 1:
                    reason = "automatic replacement requires two single-file torrents"
                elif incoming_identity is None or owner.identity is None:
                    reason = "revision identity is incomplete"
                elif not is_strict_upgrade(owner.identity, incoming_identity):
                    reason = "existing and incoming releases are not a strict revision upgrade"
                else:
                    reason = "revision conflict policy is hold"
            await self._persist_conflict(
                info=info,
                prepared=prepared,
                identity=incoming_identity,
                owner=owner,
                reason=reason,
            )
            return MediaRenameReport(
                result=RenameResult(RenameOutcome.DESTINATION_EXISTS, detail=reason),
                prepared=prepared,
            )

        return await self._run_ordinary_rename(
            info=info,
            prepared=prepared,
            identity=identity,
            bangumi_name=bangumi_name,
            episode_offset=episode_offset,
            notify_if_unchanged=method == "none",
        )

    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalize path by removing trailing slashes and standardizing separators."""
        if not path:
            return path
        # Replace backslashes with forward slashes for consistency
        normalized = path.replace("\\", "/")
        # Remove trailing slashes
        return normalized.rstrip("/")

    async def _batch_lookup_offsets(
        self, torrents_info: list[dict]
    ) -> dict[str, tuple[int, int, str]]:
        """Batch lookup offsets for all torrents in a single database session.

        Returns a dict mapping torrent_hash to
        (episode_offset, season_offset, episode_type).
        """
        result: dict[str, tuple[int, int, str]] = {}
        if not torrents_info:
            return result

        try:
            async with Database() as db:
                # Collect all hashes for batch query
                hashes = [info["hash"] for info in torrents_info]
                torrent_records = await db.torrent.search_by_qb_hashes(hashes)
                hash_to_bangumi_id = {
                    r.qb_hash: r.bangumi_id for r in torrent_records if r.bangumi_id
                }

                # Collect unique bangumi IDs to fetch
                bangumi_ids_to_fetch = set(hash_to_bangumi_id.values())

                # Also collect bangumi IDs from tags
                tag_bangumi_ids = {}
                for info in torrents_info:
                    tags = info.get("tags", "")
                    bangumi_id = self._parse_bangumi_id_from_tags(tags)
                    if bangumi_id:
                        tag_bangumi_ids[info["hash"]] = bangumi_id
                        bangumi_ids_to_fetch.add(bangumi_id)

                # Batch fetch all bangumi records
                bangumi_map = {}
                if bangumi_ids_to_fetch:
                    bangumi_records = await db.bangumi.search_ids(
                        list(bangumi_ids_to_fetch)
                    )
                    bangumi_map = {
                        b.id: b for b in bangumi_records if b and not b.deleted
                    }

                # Resolve via qb_hash/tag first (both already batched above,
                # O(1) queries regardless of torrent count).
                unresolved: list[dict] = []
                for info in torrents_info:
                    torrent_hash = info["hash"]

                    # 1. Try by qb_hash
                    bangumi_id = hash_to_bangumi_id.get(torrent_hash)
                    if bangumi_id and bangumi_id in bangumi_map:
                        b = bangumi_map[bangumi_id]
                        result[torrent_hash] = (
                            b.episode_offset,
                            b.season_offset,
                            b.episode_type,
                        )
                        continue

                    # 2. Try by tag
                    bangumi_id = tag_bangumi_ids.get(torrent_hash)
                    if bangumi_id and bangumi_id in bangumi_map:
                        b = bangumi_map[bangumi_id]
                        result[torrent_hash] = (
                            b.episode_offset,
                            b.season_offset,
                            b.episode_type,
                        )
                        continue

                    unresolved.append(info)

                # 3./4. Fall back to name/save_path matching for whatever is
                # left. Load the full bangumi list once (same idiom as
                # RSSEngine.refresh_rss / auto_tag_torrents) and match every
                # remaining torrent in memory, instead of running up to 3
                # queries per torrent (match_torrent()'s own search_all() +
                # up to 2 match_by_save_path() calls).
                if unresolved:
                    bangumi_list = await db.bangumi.search_all()
                    save_path_index = build_save_path_index(bangumi_list)
                    for info in unresolved:
                        torrent_hash = info["hash"]
                        torrent_name = info["name"]
                        save_path = info["save_path"]

                        bangumi = match_bangumi_in_list(torrent_name, bangumi_list)
                        if not bangumi:
                            # normalize_save_path() already folds "\\" -> "/"
                            # and strips trailing slashes, so a single lookup
                            # covers every variation match_by_save_path() used
                            # to try separately.
                            bangumi = save_path_index.get(
                                normalize_save_path(save_path)
                            )

                        if bangumi:
                            result[torrent_hash] = (
                                bangumi.episode_offset,
                                bangumi.season_offset,
                                bangumi.episode_type,
                            )
                        else:
                            # Default: no offset
                            result[torrent_hash] = (0, 0, "episode")

        except Exception as e:
            missing = [
                info["hash"] for info in torrents_info if info["hash"] not in result
            ]
            logger.warning(
                "Batch offset lookup failed; skipping rename for %d "
                "torrent(s) this cycle: %s",
                len(missing),
                e,
            )
            # Leave the unresolved torrents out of the map entirely so
            # rename() skips them instead of silently defaulting to (0, 0),
            # which would apply a wrong offset instead of no offset.

        return result

    async def _lookup_offsets(
        self, torrent_hash: str, torrent_name: str, save_path: str, tags: str = ""
    ) -> tuple[int, int]:
        """Look up episode and season offsets for a bangumi.

        Lookup order (most to least reliable):
        1. By qb_hash in Torrent table (links directly to bangumi via torrent record)
        2. By bangumi_id extracted from tags (handles multiple subscriptions perfectly)
        3. By torrent_name matching (handles most cases)
        4. By save_path matching (legacy fallback, may fail with multiple subscriptions)

        Args:
            torrent_hash: The qBittorrent hash to lookup in Torrent table
            torrent_name: The torrent name to match against bangumi.title_raw
            save_path: The save path to match against bangumi.save_path
            tags: Comma-separated torrent tags, may contain 'ab:ID' for bangumi_id

        Returns:
            tuple[int, int]: (episode_offset, season_offset)
        """
        try:
            async with Database() as db:
                # First try by qb_hash in Torrent table (most reliable for existing torrents)
                torrent_record = await db.torrent.search_by_qb_hash(torrent_hash)
                if torrent_record and torrent_record.bangumi_id:
                    bangumi = await db.bangumi.search_id(torrent_record.bangumi_id)
                    if bangumi and not bangumi.deleted:
                        logger.debug(
                            "Found offsets via qb_hash: ep=%s, season=%s",
                            bangumi.episode_offset,
                            bangumi.season_offset,
                        )
                        return bangumi.episode_offset, bangumi.season_offset

                # Then try by bangumi_id from tags (for newly added torrents)
                bangumi_id = self._parse_bangumi_id_from_tags(tags)
                if bangumi_id:
                    bangumi = await db.bangumi.search_id(bangumi_id)
                    if bangumi and not bangumi.deleted:
                        logger.debug(
                            "Found offsets via tag ab:%s: ep=%s, season=%s",
                            bangumi_id,
                            bangumi.episode_offset,
                            bangumi.season_offset,
                        )
                        return bangumi.episode_offset, bangumi.season_offset

                # Then try matching by torrent name
                bangumi = await db.bangumi.match_torrent(torrent_name)
                if bangumi:
                    logger.info(
                        f"Matched bangumi '{bangumi.official_title}' (id={bangumi.id}) via name, "
                        f"offsets: ep={bangumi.episode_offset}, season={bangumi.season_offset}"
                    )
                    return bangumi.episode_offset, bangumi.season_offset

                # Finally fall back to save_path matching with normalization
                normalized_save_path = self._normalize_path(save_path)
                bangumi = await db.bangumi.match_by_save_path(save_path)
                if not bangumi:
                    # Try with normalized path if exact match failed
                    bangumi = await db.bangumi.match_by_save_path(normalized_save_path)
                if bangumi:
                    logger.info(
                        f"Matched bangumi '{bangumi.official_title}' (id={bangumi.id}) via save_path, "
                        f"offsets: ep={bangumi.episode_offset}, season={bangumi.season_offset}"
                    )
                    return bangumi.episode_offset, bangumi.season_offset

                logger.info(
                    f"No bangumi match for torrent (using offset=0): "
                    f"name={torrent_name[:60] if torrent_name else 'N/A'}..."
                )
        except Exception as e:
            logger.debug("Could not lookup offsets for %s: %s", save_path, e)
        return 0, 0

    async def rename(self) -> list[Notification]:
        logger.debug("Start rename process.")
        rename_method = settings.bangumi_manage.rename_method
        pending_infos = await self.client.get_torrent_info()
        # Owner counting and Saga recovery must see tasks outside the normal
        # Bangumi/completed filter (collections, paused tasks, changed category).
        all_infos = await self.client.get_torrent_info(
            category=None, status_filter=None
        )
        info_by_hash = {info["hash"]: info for info in all_infos}
        for info in pending_infos:
            info_by_hash.setdefault(info["hash"], info)
        all_infos = list(info_by_hash.values())
        async with Database() as db:
            active_replacements = await db.rename_operation.list_active_replacements()
        active_replacement_ids = {
            operation.new_task_id for operation in active_replacements
        }
        for operation in active_replacements:
            if operation.new_task_id not in info_by_hash:
                incoming_exists = await self.client.torrent_exists(
                    operation.new_task_id
                )
                if incoming_exists is None or incoming_exists:
                    # A failed/incomplete bulk snapshot must never be treated
                    # as proof that the incoming task disappeared.
                    continue
                await self._recover_missing_replacement(operation, all_infos)
                continue
            if not any(
                info.get("hash") == operation.new_task_id for info in pending_infos
            ):
                pending_infos.append(info_by_hash[operation.new_task_id])
        # `ab:renamed` is a real terminal marker.  Filter it before file and
        # offset queries; a later V2 still sees it lazily as a possible owner.
        torrents_info = [
            info
            for info in pending_infos
            if info.get("hash") in active_replacement_ids
            or not self._has_tag(info.get("tags"), _RENAMED_TAG)
        ]
        renamed_info: list[Notification] = []
        if not torrents_info:
            logger.debug("Rename process finished: no pending torrents")
            return renamed_info

        all_files = await asyncio.gather(
            *[self.client.get_torrent_files(info["hash"]) for info in torrents_info]
        )
        offset_map = await self._batch_lookup_offsets(torrents_info)
        for info, files in zip(torrents_info, all_files):
            torrent_hash = info["hash"]
            torrent_name = info["name"]
            save_path = info["save_path"]
            if torrent_hash not in offset_map:
                # Offset lookup failed for this torrent this cycle (see
                # _batch_lookup_offsets) -- skip renaming rather than
                # guessing offset (0, 0), which could misname episodes.
                logger.warning(
                    "Skipping %s: offset lookup failed this cycle",
                    torrent_name,
                )
                continue
            media_list, subtitle_list = check_files(files)
            bangumi_name, season = path_to_bangumi(save_path, torrent_name)
            episode_offset, season_offset, episode_type = offset_map[torrent_hash]
            kwargs = {
                "torrent_name": torrent_name,
                "bangumi_name": bangumi_name,
                "method": rename_method,
                "season": season,
                "_hash": torrent_hash,
                "episode_offset": episode_offset,
                "season_offset": season_offset,
                "episode_type": episode_type,
                "existing_tags": info.get("tags"),
            }
            if len(media_list) == 1:
                report = await self._process_single_torrent(
                    info=info,
                    files=files,
                    media_path=media_list[0],
                    all_infos=all_infos,
                    bangumi_name=bangumi_name,
                    season=season,
                    method=rename_method,
                    episode_offset=episode_offset,
                    season_offset=season_offset,
                    episode_type=episode_type,
                )
                if report.notification:
                    renamed_info.append(report.notification)
                if report.result.succeeded:
                    if subtitle_list:
                        await self.rename_subtitles(
                            subtitle_list=subtitle_list, **kwargs
                        )
                    if rename_method not in ("none", "normal"):
                        await self._mark_renamed(torrent_hash, info.get("tags"))
            elif len(media_list) > 1:
                logger.info("Start rename collection")
                file_sizes = {f["name"]: f.get("size") or 0 for f in files}
                collection_complete = await self.rename_collection(
                    media_list=media_list,
                    file_sizes=file_sizes,
                    mark_complete=False,
                    torrent_info=info,
                    **kwargs,
                )
                if collection_complete and subtitle_list:
                    await self.rename_subtitles(subtitle_list=subtitle_list, **kwargs)
                if collection_complete:
                    if rename_method not in ("none", "normal"):
                        await self._mark_renamed(torrent_hash, info.get("tags"))
                    await self.client.set_category(torrent_hash, "BangumiCollection")
            else:
                logger.warning(f"{torrent_name} has no media file")
        async with Database() as db:
            await db.rename_operation.prune_done(
                datetime.now(timezone.utc) - timedelta(days=30)
            )
        logger.debug("Rename process finished.")
        return renamed_info
