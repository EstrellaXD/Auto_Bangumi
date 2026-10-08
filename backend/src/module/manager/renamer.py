"""重命名编排：拉取待处理种子 → 查偏移 → 生成目标路径 → 执行重命名。

路径生成见 ``rename_strategy``，revision 替换事务见 ``revision_saga``。
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta, timezone

from module.conf import settings
from module.database import Database
from module.database.bangumi import (
    build_save_path_index,
    match_bangumi_in_list,
    normalize_save_path,
)
from module.downloader import DownloadClient, RenameOutcome, RenameResult
from module.downloader.path import check_files, is_ep, path_to_bangumi
from module.models import Notification
from module.notification import RenameConflictEvent
from module.parser import TitleParser

from .rename_strategy import (
    adjust_episode,
    format_episode,
    gen_movie_extra_path,
    gen_path,
)
from .revision_policy import is_strict_upgrade, parse_revision_identity
from .revision_saga import (
    MediaRenameReport,
    PreparedMediaRename,
    RevisionOwner,
    RevisionSaga,
    parse_bangumi_id_from_tags,
    retry_is_due,
)

logger = logging.getLogger(__name__)

# 处理完成标记：供外部脚本（filebot、hlink 等）过滤 AB 已重命名的任务 (#147)。
# 语义 = 顶层媒体文件全部就位；字幕在同一轮循环里紧随其后重命名，深层
# 嵌套文件（特典/花絮）设计上从不重命名——两者都不阻塞打标
_RENAMED_TAG = "ab:renamed"

__all__ = [
    "MediaRenameReport",
    "PreparedMediaRename",
    "Renamer",
    "RevisionOwner",
]


class Renamer:
    def __init__(self, client: DownloadClient):
        self.client = client
        self._parser = TitleParser()
        self.events: list[RenameConflictEvent] = []
        self.saga = RevisionSaga(
            client,
            events=self.events,
            downloader_type=self._downloader_type,
            mark_renamed=self._mark_renamed,
        )

    _adjust_episode = staticmethod(adjust_episode)
    _format_episode = staticmethod(format_episode)
    gen_path = staticmethod(gen_path)
    _gen_movie_extra_path = staticmethod(gen_movie_extra_path)
    _parse_bangumi_id_from_tags = staticmethod(parse_bangumi_id_from_tags)
    _retry_is_due = staticmethod(retry_is_due)

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
        if report.result.succeeded and method != "none":
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
        return await self.saga.execute_media_rename(
            prepared=prepared,
            bangumi_name=bangumi_name,
            _hash=_hash,
            episode_offset=episode_offset,
        )

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
                            report = await self.saga.run_ordinary_rename(
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
        if all_renamed and mark_complete and method != "none":
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
    def _has_tag(tags: str | None, expected: str) -> bool:
        return expected in (tag.strip() for tag in (tags or "").split(","))

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
                await self.saga.emit_conflict_once(
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
                notification = await self.saga.advance_replacement(
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

        incoming_identity, owners = await self.saga.find_revision_owners(
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
                notification = await self.saga.start_replacement(
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
            await self.saga.persist_conflict(
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

        return await self.saga.run_ordinary_rename(
            info=info,
            prepared=prepared,
            identity=identity,
            bangumi_name=bangumi_name,
            episode_offset=episode_offset,
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
                await self.saga.recover_missing_replacement(operation, all_infos)
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
                    if rename_method != "none":
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
                    if rename_method != "none":
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
