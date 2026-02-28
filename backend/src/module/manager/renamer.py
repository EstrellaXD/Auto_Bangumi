import asyncio
import logging
import time
from pathlib import PurePath

from module.conf import settings
from module.database import Database
from module.database.bangumi import (
    build_save_path_index,
    match_bangumi_in_list,
    normalize_save_path,
)
from module.downloader import DownloadClient
from module.downloader.path import check_files, is_ep, path_to_bangumi
from module.models import EpisodeFile, Notification, SubtitleFile
from module.parser import TitleParser

logger = logging.getLogger(__name__)

# Module-level cache to track pending renames that qBittorrent hasn't processed yet
# Key: (torrent_hash, old_path, new_path), Value: timestamp of last attempt
# This prevents spamming the same rename when qBittorrent returns 200 but doesn't actually rename
_pending_renames: dict[tuple[str, str, str], float] = {}
_PENDING_RENAME_COOLDOWN = 300  # 5 minutes cooldown before retrying same rename
_CLEANUP_INTERVAL = 60  # Clean up pending cache at most once per minute
_last_cleanup_time: float = 0

# 处理完成标记：供外部脚本（filebot、hlink 等）过滤 AB 已重命名的任务 (#147)。
# 语义 = 顶层媒体文件全部就位；字幕在同一轮循环里紧随其后重命名，深层
# 嵌套文件（特典/花絮）设计上从不重命名——两者都不阻塞打标
_RENAMED_TAG = "ab:renamed"


class Renamer:
    def __init__(self, client: DownloadClient):
        self.client = client
        self._parser = TitleParser()
        self._offset_cache: dict[str, tuple[int, int]] = {}

    @staticmethod
    def _cleanup_pending_cache():
        """Clean up expired entries from pending renames cache (throttled)."""
        global _last_cleanup_time
        current_time = time.time()
        if current_time - _last_cleanup_time < _CLEANUP_INTERVAL:
            return
        _last_cleanup_time = current_time
        expired_keys = [
            k
            for k, v in _pending_renames.items()
            if current_time - v > _PENDING_RENAME_COOLDOWN * 2
        ]
        for k in expired_keys:
            _pending_renames.pop(k, None)

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
        ep = self._parser.torrent_parser(
            torrent_name=torrent_name,
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
            if media_path == new_path:
                # 已符合目标命名（如重启后再次扫描）：视为处理完成。
                # none/normal 是直通方法，没有"重命名完成"的语义，不打标
                if method not in ("none", "normal"):
                    await self._mark_renamed(_hash, existing_tags)
            else:
                # Check if this rename was recently attempted but didn't take effect
                # (qBittorrent can return 200 but delay actual rename while seeding)
                pending_key = (_hash, media_path, new_path)
                last_attempt = _pending_renames.get(pending_key)
                if (
                    last_attempt
                    and (time.time() - last_attempt) < _PENDING_RENAME_COOLDOWN
                ):
                    logger.debug("Skipping rename (pending cooldown): %s", media_path)
                    return None

                if await self.client.rename_torrent_file(
                    _hash=_hash, old_path=media_path, new_path=new_path
                ):
                    # Rename verified successful, remove from pending cache
                    _pending_renames.pop(pending_key, None)
                    await self._mark_renamed(_hash, existing_tags)
                    # Season comes from folder which already has offset applied
                    # Only apply episode offset
                    return Notification(
                        official_title=bangumi_name,
                        season=ep.season,
                        episode=self._adjust_episode(ep.episode, episode_offset),
                    )
                else:
                    # Rename API returned success but file wasn't actually renamed
                    # Add to pending cache to avoid spamming
                    _pending_renames[pending_key] = time.time()
                    # Periodic cleanup of expired entries (at most once per minute)
                    self._cleanup_pending_cache()
        else:
            logger.warning(f"{media_path} parse failed")
            if settings.bangumi_manage.remove_bad_torrent:
                await self.client.delete_torrent(hashes=_hash)
        return None

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
                        renamed = await self.client.rename_torrent_file(
                            _hash=_hash, old_path=media_path, new_path=new_path
                        )
                        if not renamed:
                            all_renamed = False
                            logger.warning(f"{media_path} rename failed")
                            # Delete bad torrent.
                            if settings.bangumi_manage.remove_bad_torrent:
                                await self.client.delete_torrent(_hash)
                                break
                else:
                    # 解析失败的媒体文件不会被重命名——不能算处理完成
                    all_renamed = False
        # 全部媒体文件就位（含本轮无需改名的情况）才算处理完成；
        # none/normal 直通方法没有"重命名完成"的语义，不打标
        if all_renamed and method not in ("none", "normal"):
            await self._mark_renamed(_hash, existing_tags)

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
        # Get torrent info
        logger.debug("Start rename process.")
        rename_method = settings.bangumi_manage.rename_method
        torrents_info = await self.client.get_torrent_info()
        renamed_info: list[Notification] = []
        # Fetch all torrent files concurrently
        all_files = await asyncio.gather(
            *[self.client.get_torrent_files(info["hash"]) for info in torrents_info]
        )
        # Batch lookup all offsets in a single database session
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
            # Use pre-fetched offsets
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
                # 处理完成后打 ab:renamed 标签用；已带标签则跳过 API 调用
                "existing_tags": info.get("tags"),
            }
            # Rename single media file
            if len(media_list) == 1:
                notify_info = await self.rename_file(media_path=media_list[0], **kwargs)
                if notify_info:
                    renamed_info.append(notify_info)
                # Rename subtitle file
                if len(subtitle_list) > 0:
                    await self.rename_subtitles(subtitle_list=subtitle_list, **kwargs)
            # Rename collection
            elif len(media_list) > 1:
                logger.info("Start rename collection")
                # 传入各文件体积，供多文件电影种子选出正片主文件
                file_sizes = {f["name"]: f.get("size") or 0 for f in files}
                await self.rename_collection(
                    media_list=media_list, file_sizes=file_sizes, **kwargs
                )
                if len(subtitle_list) > 0:
                    await self.rename_subtitles(subtitle_list=subtitle_list, **kwargs)
                await self.client.set_category(torrent_hash, "BangumiCollection")
            else:
                logger.warning(f"{torrent_name} has no media file")
        logger.debug("Rename process finished.")
        return renamed_info
