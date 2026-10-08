import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import PurePath
from typing import Any

from ab_sdk import points
from ab_sdk.events import FileRenamed, OrganizedFile, TorrentOrganized
from ab_sdk.rename import (
    ConflictDecision,
    ConflictRequest,
    FileKind,
    RenameInput,
    RenameSkipped,
    RevisionTask,
)
from module.conf import settings
from module.database import Database
from module.database.bangumi import (
    build_save_path_index,
    match_bangumi_in_list,
    normalize_save_path,
)
from module.downloader import (
    DownloadClient,
    RenameOutcome,
    RenameResult,
    downloader_ids,
)
from module.downloader.path import check_files, is_ep, path_to_bangumi
from module.models import EpisodeFile, Notification, SubtitleFile
from module.notification import (
    DownloaderUnavailableEvent,
    RenameSkippedEvent,
    SystemEvent,
)
from module.parser import TitleParser
from module.plugin import host as plugin_host
from module.plugin.registry import ProviderEntry

from .rename_strategies import NO_RENAME
from .revision_policy import (
    is_strict_upgrade,
    parse_revision_identity,
    revision_snapshot,
)
from .revision_saga import (
    _RENAMED_TAG,
    MediaRenameReport,
    PreparedMediaRename,
    RevisionSaga,
)

logger = logging.getLogger(__name__)

# 上一轮不可用的下载器实例：只在「可用 → 不可用」时通知一次
_unavailable: set[str] = set()
# 已记录过「未登记」日志的重命名方式（每个进程只记一次，重新登记后清除）
_missing_methods: set[str] = set()
# 已发布过的 TorrentOrganized（种子 hash → 最终文件）。未打 ab:renamed 标签的
# 种子（重命名方式为 none）每轮都会重新处理，文件不变时不重复发布。
# ponytail: 进程内字典，重启后重发一次（事件约定为至少一次）；条目随种子数增长
_organized_published: dict[str, tuple[OrganizedFile, ...]] = {}
# 已发送过「文件未重命名」通知的 (种子 hash, 原因)
_skip_notified: set[tuple[str, str]] = set()


def _rename_strategy(method: str | ProviderEntry) -> ProviderEntry:
    """按 slots.rename_strategy 取重命名策略；未登记（如 rename 插件未启用）时记录一次
    日志并按 none 处理。已解析的策略原样返回：一轮重命名只解析一次，轮中插件
    被停用也不会让同一种子的文件名与 ab:renamed 标签来自不同策略。"""
    if isinstance(method, ProviderEntry):
        return method
    strategies = plugin_host.get_registry().providers(points.RENAME_STRATEGY)
    entry = strategies.get(method)
    if entry is not None:
        _missing_methods.discard(method)
        return entry
    if method not in _missing_methods:
        _missing_methods.add(method)
        logger.warning(
            "[Renamer] 重命名方式 %s 未登记（提供它的插件未启用？），文件保留原名",
            method,
        )
    return strategies[NO_RENAME]


def _valid_name(result: Any) -> bool:
    return isinstance(result, RenameSkipped) or (
        isinstance(result, str) and result != ""
    )


def _target_name(entry: ProviderEntry, f: RenameInput) -> str:
    """调用重命名策略。策略给不出合法名字时抛出 RenameSkipped。

    插件策略经 runner 调用：异常与无效返回值计入熔断；策略主动抛出的
    RenameSkipped（输入或用户配置有问题）不计入。
    """

    def call(strategy: Any) -> str | RenameSkipped:
        try:
            return strategy.target_name(f)
        except RenameSkipped as e:
            return e

    ok, result = plugin_host.call_sync(entry, points.RENAME_STRATEGY, call, _valid_name)
    if isinstance(result, RenameSkipped):
        raise result
    if not ok:
        raise RenameSkipped(f"重命名方式 {entry.id} 执行失败，详见日志")
    return result


def _downloader_path(save_path: str, name: str) -> str:
    """下载器视角的绝对路径，统一以 "/" 分隔。"""
    relative = name.replace("\\", "/")
    return f"{normalize_save_path(save_path)}/{relative}"


class Renamer(RevisionSaga):
    def __init__(self, client: DownloadClient):
        self.client = client
        self._parser = TitleParser()
        self.events: list[SystemEvent] = []
        # 本轮各种子的实际重命名 (原路径, 新路径, 类别) 与被跳过的原因
        self._moves: dict[str, list[tuple[str, str, FileKind]]] = {}
        self._skipped: dict[str, str] = {}

    @staticmethod
    def gen_path(
        file_info: EpisodeFile | SubtitleFile,
        bangumi_name: str,
        method: str | ProviderEntry,
        episode_offset: int = 0,
    ) -> str:
        """按重命名方式生成种子内的目标路径。

        策略给不出合法名字时抛出 RenameSkipped，调用方保留原文件名。
        """
        # Season comes from the folder name which already includes the offset
        # (folder is now "Season {season + season_offset}")
        # So we use file_info.season directly without applying offset again
        # 注意：group_tag 只影响 qB RSS 规则名（downloader/path.py 的 rule_name），
        # 从不写进重命名后的文件名——已有做种媒体库的文件名必须保持稳定，
        # 否则升级后会触发整库批量重命名，破坏 Plex/Jellyfin 索引与硬链接
        f = RenameInput(
            kind="subtitle" if isinstance(file_info, SubtitleFile) else "media",
            media_path=file_info.media_path,
            title=file_info.title,
            bangumi_name=bangumi_name,
            season=file_info.season,
            episode=Renamer._adjust_episode(file_info.episode, episode_offset),
            suffix=file_info.suffix,
            episode_type=file_info.episode_type,
            language=(
                file_info.language if isinstance(file_info, SubtitleFile) else ""
            ),
            group=file_info.group,
        )
        return _target_name(_rename_strategy(method), f)

    def _prepare_media_rename(
        self,
        *,
        torrent_name: str,
        media_path: str,
        bangumi_name: str,
        method: str | ProviderEntry,
        season: int,
        episode_offset: int = 0,
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
            ),
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

    def _skip(self, _hash: str, path: str, error: RenameSkipped) -> MediaRenameReport:
        """策略给不出名字：保留原文件名，记录原因（本轮结束时通知、不打标签）。"""
        logger.warning("[Renamer] %s 保留原名：%s", path, error)
        self._skipped.setdefault(_hash, str(error))
        return MediaRenameReport(
            result=RenameResult(RenameOutcome.RETRYABLE_FAILURE, detail=str(error))
        )

    async def rename_collection(
        self,
        media_list: list[str],
        bangumi_name: str,
        season: int,
        method: str | ProviderEntry,
        _hash: str,
        episode_offset: int = 0,
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
                    try:
                        new_path = self.gen_path(
                            ep,
                            bangumi_name,
                            method=method,
                            episode_offset=episode_offset,
                        )
                    except RenameSkipped as e:
                        self._skip(_hash, media_path, e)
                        all_renamed = False
                        continue
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
                            if result.outcome is RenameOutcome.RENAMED:
                                self._record_move(_hash, media_path, new_path, "media")
                        if not result.succeeded:
                            all_renamed = False
                            logger.warning(f"{media_path} rename failed")
                else:
                    # 解析失败的媒体文件不会被重命名——不能算处理完成
                    all_renamed = False
        if all_renamed and mark_complete and _rename_strategy(method).id != NO_RENAME:
            await self._mark_renamed(_hash, existing_tags)
        return all_renamed

    async def rename_subtitles(
        self,
        subtitle_list: list[str],
        torrent_name: str,
        bangumi_name: str,
        season: int,
        method: str | ProviderEntry,
        _hash,
        episode_offset: int = 0,
        episode_type: str = "episode",
        **kwargs,
    ):
        for subtitle_path in subtitle_list:
            sub = self._parser.torrent_parser(
                torrent_path=subtitle_path,
                torrent_name=torrent_name,
                season=season,
                file_type="subtitle",
                episode_type=episode_type,
            )
            if sub:
                try:
                    new_path = self.gen_path(
                        sub,
                        bangumi_name,
                        method=method,
                        episode_offset=episode_offset,
                    )
                except RenameSkipped as e:
                    self._skip(_hash, subtitle_path, e)
                    continue
                if subtitle_path != new_path:
                    # Skip verification for subtitles to reduce latency
                    renamed = await self.client.rename_torrent_file(
                        _hash=_hash,
                        old_path=subtitle_path,
                        new_path=new_path,
                        verify=False,
                    )
                    if renamed.outcome is RenameOutcome.RENAMED:
                        self._record_move(_hash, subtitle_path, new_path, "subtitle")
                    if not renamed:
                        logger.warning(f"{subtitle_path} rename failed")

    @staticmethod
    def _has_tag(tags: str | None, expected: str) -> bool:
        return expected in (tag.strip() for tag in (tags or "").split(","))

    async def _process_single_torrent(
        self,
        *,
        info: dict,
        files: list[dict],
        media_path: str,
        all_infos: list[dict],
        bangumi_name: str,
        season: int,
        method: str | ProviderEntry,
        episode_offset: int,
        episode_type: str,
    ) -> MediaRenameReport:
        try:
            prepared = self._prepare_media_rename(
                torrent_name=info["name"],
                media_path=media_path,
                bangumi_name=bangumi_name,
                method=method,
                season=season,
                episode_offset=episode_offset,
                episode_type=episode_type,
            )
        except RenameSkipped as e:
            return self._skip(info["hash"], media_path, e)
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
            decision = self._decide_conflict(
                ConflictRequest(
                    target_path=prepared.target_path,
                    incoming=RevisionTask(
                        info["hash"],
                        info.get("name", ""),
                        len(files),
                        revision_snapshot(incoming_identity),
                    ),
                    owners=tuple(
                        RevisionTask(
                            o.info["hash"],
                            o.info.get("name", ""),
                            len(o.files),
                            revision_snapshot(o.identity),
                        )
                        for o in owners
                    ),
                    strict_upgrade=bool(
                        owner is not None
                        and incoming_identity is not None
                        and owner.identity is not None
                        and is_strict_upgrade(owner.identity, incoming_identity)
                    ),
                )
            )
            # 替换 saga 只支持「唯一占用者、双方单文件、身份完整」的情形
            if (
                decision.action == "replace"
                and owner is not None
                and len(files) == 1
                and len(owner.files) == 1
                and incoming_identity is not None
                and owner.identity is not None
            ):
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

            reason = decision.reason or "automatic replacement is not possible"
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
        )

    def _finish_torrent(
        self,
        info: dict,
        media_list: list[str],
        subtitle_list: list[str],
        method: str,
        organized: bool,
    ) -> None:
        """发布该种子本轮的 file.renamed；整理完成时发布 torrent.organized；
        有文件因策略给不出名字而保留原名时改为发一条通知（同一原因只发一次）。"""
        torrent_hash = info["hash"]
        save_path = info["save_path"]
        bangumi_id = self._parse_bangumi_id_from_tags(info.get("tags"))
        final: dict[str, str] = {}
        for old, new, kind in self._moves.pop(torrent_hash, []):
            final[old] = new
            plugin_host.publish(
                FileRenamed(
                    bangumi_id=bangumi_id,
                    old_path=_downloader_path(save_path, old),
                    new_path=_downloader_path(save_path, new),
                    file_kind=kind,
                    downloader_id=self.client.instance_id,
                )
            )
        reason = self._skipped.pop(torrent_hash, None)
        if reason is not None:
            if (torrent_hash, reason) not in _skip_notified:
                _skip_notified.add((torrent_hash, reason))
                self.events.append(
                    RenameSkippedEvent(
                        task_id=torrent_hash,
                        torrent_name=info["name"],
                        strategy=method,
                        reason=reason,
                    )
                )
            return
        if not organized:
            return
        kinds: tuple[tuple[list[str], FileKind], ...] = (
            (media_list, "media"),
            (subtitle_list, "subtitle"),
        )
        files = tuple(
            OrganizedFile(_downloader_path(save_path, final.get(name, name)), kind)
            for names, kind in kinds
            for name in names
        )
        if _organized_published.get(torrent_hash) == files:
            return
        _organized_published[torrent_hash] = files
        plugin_host.publish(
            TorrentOrganized(
                torrent_hash=torrent_hash,
                bangumi_id=bangumi_id,
                files=files,
                downloader_id=self.client.instance_id,
            )
        )

    @staticmethod
    def _decide_conflict(request: ConflictRequest) -> ConflictDecision:
        # 选中的策略未登记（插件停用或被熔断）、抛出异常或返回值无效时按 hold
        # 处理，不会误删旧版本；插件的失败已计入熔断
        policies = plugin_host.get_registry().providers(points.CONFLICT_POLICY)
        hold = policies["hold"]
        entry = policies.get(settings.plugins.slots.conflict_policy) or hold
        ok, decision = plugin_host.call_sync(
            entry,
            points.CONFLICT_POLICY,
            lambda policy: policy.decide(request),
            lambda result: isinstance(result, ConflictDecision),
        )
        return decision if ok else hold.factory().decide(request)

    async def _batch_lookup_offsets(
        self, torrents_info: list[dict]
    ) -> dict[str, tuple[int, str]]:
        """Batch lookup offsets for all torrents in a single database session.

        Returns a dict mapping torrent_hash to (episode_offset, episode_type).
        """
        result: dict[str, tuple[int, str]] = {}
        if not torrents_info:
            return result

        try:
            async with Database() as db:
                # Collect all hashes for batch query
                hashes = [info["hash"] for info in torrents_info]
                torrent_records = await db.torrent.search_by_qb_hashes(hashes)
                # 同一 hash 在多个实例都有记录时，以本实例的记录为准（排在后面覆盖）
                torrent_records.sort(
                    key=lambda r: r.downloader_id == self.client.instance_id
                )
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
                        result[torrent_hash] = (b.episode_offset, b.episode_type)
                        continue

                    # 2. Try by tag
                    bangumi_id = tag_bangumi_ids.get(torrent_hash)
                    if bangumi_id and bangumi_id in bangumi_map:
                        b = bangumi_map[bangumi_id]
                        result[torrent_hash] = (b.episode_offset, b.episode_type)
                        continue

                    unresolved.append(info)

                # 3./4. Fall back to name/save_path matching for whatever is
                # left. Load the full bangumi list once (same idiom as
                # RSSEngine.refresh_rss / auto_tag_torrents) and match every
                # remaining torrent in memory, instead of querying per torrent.
                if unresolved:
                    bangumi_list = await db.bangumi.search_all()
                    save_path_index = build_save_path_index(bangumi_list)
                    for info in unresolved:
                        torrent_hash = info["hash"]
                        torrent_name = info["name"]
                        save_path = info["save_path"]

                        bangumi = match_bangumi_in_list(torrent_name, bangumi_list)
                        if not bangumi:
                            # normalize_save_path() folds "\\" -> "/" and strips
                            # trailing slashes, so one lookup covers every variation.
                            bangumi = save_path_index.get(
                                normalize_save_path(save_path)
                            )

                        if bangumi:
                            result[torrent_hash] = (
                                bangumi.episode_offset,
                                bangumi.episode_type,
                            )
                        else:
                            # Default: no offset
                            result[torrent_hash] = (0, "episode")

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
            # rename() skips them instead of silently defaulting to offset 0,
            # which would apply a wrong offset instead of no offset.

        return result

    async def rename(self) -> list[Notification]:
        logger.debug("Start rename process.")
        configured = settings.plugins.slots.rename_strategy
        strategy = _rename_strategy(configured)
        # 选中的策略未登记（重载窗口、熔断、模板失效）时文件保留原名，但原名不是
        # 最终文件名：策略恢复后还会改名，这时发布 torrent.organized 会让订阅者
        # （如硬链接）按两个文件名各处理一次
        final_names = strategy.id == configured
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
        # 只有一个实例时不按实例过滤：键里含主机哈希，改了主机地址（同一个
        # 下载器）后进行中的事务仍要恢复；多个实例时只恢复本实例的
        instance_key = self._downloader_type() if len(downloader_ids()) > 1 else None
        async with Database() as db:
            active_replacements = await db.rename_operation.list_active_replacements(
                instance_key
            )
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
                # guessing offset 0, which could misname episodes.
                logger.warning(
                    "Skipping %s: offset lookup failed this cycle",
                    torrent_name,
                )
                continue
            media_list, subtitle_list = check_files(files)
            bangumi_name, season = path_to_bangumi(
                save_path, torrent_name, self.client.instance.path
            )
            episode_offset, episode_type = offset_map[torrent_hash]
            kwargs = {
                "torrent_name": torrent_name,
                "bangumi_name": bangumi_name,
                "method": strategy,
                "season": season,
                "_hash": torrent_hash,
                "episode_offset": episode_offset,
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
                    method=strategy,
                    episode_offset=episode_offset,
                    episode_type=episode_type,
                )
                if report.notification:
                    renamed_info.append(report.notification)
                if report.result.succeeded:
                    if subtitle_list:
                        await self.rename_subtitles(
                            subtitle_list=subtitle_list, **kwargs
                        )
                    if strategy.id != NO_RENAME and torrent_hash not in self._skipped:
                        await self._mark_renamed(torrent_hash, info.get("tags"))
                self._finish_torrent(
                    info,
                    media_list,
                    subtitle_list,
                    strategy.id,
                    report.result.succeeded and final_names,
                )
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
                    if strategy.id != NO_RENAME and torrent_hash not in self._skipped:
                        await self._mark_renamed(torrent_hash, info.get("tags"))
                    await self.client.set_category(torrent_hash, "BangumiCollection")
                self._finish_torrent(
                    info,
                    media_list,
                    subtitle_list,
                    strategy.id,
                    collection_complete and final_names,
                )
            else:
                logger.warning(f"{torrent_name} has no media file")
        async with Database() as db:
            await db.rename_operation.prune_done(
                datetime.now(timezone.utc) - timedelta(days=30)
            )
        logger.debug("Rename process finished.")
        return renamed_info


async def rename_all() -> tuple[list[Notification], list[SystemEvent]]:
    """逐个下载器实例运行一轮重命名。

    进不去的实例（连不上、凭据被拒、Provider 未登记）跳过，不影响其它实例；
    它从可用变为不可用时产生一条 :class:`DownloaderUnavailableEvent`。
    """
    renamed: list[Notification] = []
    events: list[SystemEvent] = []
    for instance_id in downloader_ids():
        client: DownloadClient | None = None
        try:
            client = DownloadClient(instance_id)
            await client.__aenter__()
        except Exception as e:
            logger.warning("Downloader %s unavailable, skipped: %s", instance_id, e)
            if instance_id not in _unavailable:
                _unavailable.add(instance_id)
                events.append(
                    DownloaderUnavailableEvent(
                        host=settings.downloader_instance(instance_id).host,
                        reason=(client and client.last_auth_error) or "unreachable",
                        instance_id=instance_id,
                    )
                )
            continue
        _unavailable.discard(instance_id)
        try:
            renamer = Renamer(client)
            renamed += await renamer.rename()
            events += renamer.events
        finally:
            await client.__aexit__(None, None, None)
    return renamed, events
