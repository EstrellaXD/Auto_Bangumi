import asyncio
import logging
import re
import time

from module.conf import settings
from module.database import Database
from module.downloader import DownloadClient
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


class Renamer(DownloadClient):
    def __init__(self):
        super().__init__()
        self._parser = TitleParser()
        self.check_pool = {}
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
        logger.debug(f"Checked {torrent_count} files")

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
        # Apply episode offset
        original_episode = int(file_info.episode)
        adjusted_episode = original_episode + episode_offset
        # Episode 0 is valid (specials, OVAs, etc.) - only handle truly negative results
        if adjusted_episode < 0:
            # Offset would make episode negative - ignore the offset
            adjusted_episode = original_episode
            logger.warning(
                f"[Renamer] Episode offset {episode_offset} would make episode {original_episode} negative, ignoring offset"
            )
        episode = f"0{adjusted_episode}" if adjusted_episode < 10 else adjusted_episode
        if method == "none" or method == "subtitle_none":
            return file_info.media_path
        elif method == "pn":
            return f"{file_info.title} S{season}E{episode}{file_info.suffix}"
        elif method == "advance":
            return f"{bangumi_name} S{season}E{episode}{file_info.suffix}"
        elif method == "normal":
            logger.warning("[Renamer] Normal rename method is deprecated.")
            return file_info.media_path
        elif method == "subtitle_pn":
            return f"{file_info.title} S{season}E{episode}.{file_info.language}{file_info.suffix}"
        elif method == "subtitle_advance":
            return f"{bangumi_name} S{season}E{episode}.{file_info.language}{file_info.suffix}"
        else:
            logger.error(f"[Renamer] Unknown rename method: {method}")
            return file_info.media_path

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
        **kwargs,
    ):
        ep = self._parser.torrent_parser(
            torrent_name=torrent_name,
            torrent_path=media_path,
            season=season,
        )
        if ep:
            new_path = self.gen_path(
                ep,
                bangumi_name,
                method=method,
                episode_offset=episode_offset,
                season_offset=season_offset,
            )
            if media_path != new_path:
                if new_path not in self.check_pool.keys():
                    # Check if this rename was recently attempted but didn't take effect
                    # (qBittorrent can return 200 but delay actual rename while seeding)
                    pending_key = (_hash, media_path, new_path)
                    last_attempt = _pending_renames.get(pending_key)
                    if (
                        last_attempt
                        and (time.time() - last_attempt) < _PENDING_RENAME_COOLDOWN
                    ):
                        logger.debug(
                            f"[Renamer] Skipping rename (pending cooldown): {media_path}"
                        )
                        return None

                    if await self.rename_torrent_file(
                        _hash=_hash, old_path=media_path, new_path=new_path
                    ):
                        # Rename verified successful, remove from pending cache
                        _pending_renames.pop(pending_key, None)
                        # Season comes from folder which already has offset applied
                        # Only apply episode offset
                        original_ep = int(ep.episode)
                        adjusted_episode = original_ep + episode_offset
                        # Episode 0 is valid - only handle truly negative results
                        if adjusted_episode < 0:
                            adjusted_episode = original_ep
                        return Notification(
                            official_title=bangumi_name,
                            season=ep.season,
                            episode=adjusted_episode,
                        )
                    else:
                        # Rename API returned success but file wasn't actually renamed
                        # Add to pending cache to avoid spamming
                        _pending_renames[pending_key] = time.time()
                        # Periodic cleanup of expired entries (at most once per minute)
                        self._cleanup_pending_cache()
        else:
            logger.warning(f"[Renamer] {media_path} parse failed")
            if settings.bangumi_manage.remove_bad_torrent:
                await self.delete_torrent(hashes=_hash)
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
        **kwargs,
    ):
        for media_path in media_list:
            if self.is_ep(media_path):
                ep = self._parser.torrent_parser(
                    torrent_path=media_path,
                    season=season,
                )
                if ep:
                    new_path = self.gen_path(
                        ep,
                        bangumi_name,
                        method=method,
                        episode_offset=episode_offset,
                        season_offset=season_offset,
                    )
                    if media_path != new_path:
                        renamed = await self.rename_torrent_file(
                            _hash=_hash, old_path=media_path, new_path=new_path
                        )
                        if not renamed:
                            logger.warning(f"[Renamer] {media_path} rename failed")
                            # Delete bad torrent.
                            if settings.bangumi_manage.remove_bad_torrent:
                                await self.delete_torrent(_hash)
                                break

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
        **kwargs,
    ):
        method = "subtitle_" + method
        for subtitle_path in subtitle_list:
            sub = self._parser.torrent_parser(
                torrent_path=subtitle_path,
                torrent_name=torrent_name,
                season=season,
                file_type="subtitle",
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
                    renamed = await self.rename_torrent_file(
                        _hash=_hash,
                        old_path=subtitle_path,
                        new_path=new_path,
                        verify=False,
                    )
                    if not renamed:
                        logger.warning(f"[Renamer] {subtitle_path} rename failed")

    @staticmethod
    def _parse_bangumi_id_from_tags(tags: str) -> int | None:
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

    def _batch_lookup_offsets(
        self, torrents_info: list[dict]
    ) -> dict[str, tuple[int, int]]:
        """Batch lookup offsets for all torrents in a single database session.

        Returns a dict mapping torrent_hash to (episode_offset, season_offset).
        """
        result: dict[str, tuple[int, int]] = {}
        if not torrents_info:
            return result

        try:
            with Database() as db:
                # Collect all hashes for batch query
                hashes = [info["hash"] for info in torrents_info]
                torrent_records = db.torrent.search_by_qb_hashes(hashes)
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
                    bangumi_records = db.bangumi.search_ids(list(bangumi_ids_to_fetch))
                    bangumi_map = {
                        b.id: b for b in bangumi_records if b and not b.deleted
                    }

                # Now resolve offsets for each torrent
                for info in torrents_info:
                    torrent_hash = info["hash"]
                    torrent_name = info["name"]
                    save_path = info["save_path"]

                    # 1. Try by qb_hash
                    bangumi_id = hash_to_bangumi_id.get(torrent_hash)
                    if bangumi_id and bangumi_id in bangumi_map:
                        b = bangumi_map[bangumi_id]
                        result[torrent_hash] = (b.episode_offset, b.season_offset)
                        continue

                    # 2. Try by tag
                    bangumi_id = tag_bangumi_ids.get(torrent_hash)
                    if bangumi_id and bangumi_id in bangumi_map:
                        b = bangumi_map[bangumi_id]
                        result[torrent_hash] = (b.episode_offset, b.season_offset)
                        continue

                    # 3. Try by torrent name (individual query, but less common path)
                    bangumi = db.bangumi.match_torrent(torrent_name)
                    if bangumi:
                        result[torrent_hash] = (
                            bangumi.episode_offset,
                            bangumi.season_offset,
                        )
                        continue

                    # 4. Try by save_path (individual query, fallback)
                    normalized_save_path = self._normalize_path(save_path)
                    bangumi = db.bangumi.match_by_save_path(save_path)
                    if not bangumi:
                        bangumi = db.bangumi.match_by_save_path(normalized_save_path)
                    if bangumi:
                        result[torrent_hash] = (
                            bangumi.episode_offset,
                            bangumi.season_offset,
                        )
                        continue

                    # Default: no offset
                    result[torrent_hash] = (0, 0)

        except Exception as e:
            logger.debug(f"[Renamer] Batch offset lookup failed: {e}")
            # Fall back to individual lookups on error
            for info in torrents_info:
                if info["hash"] not in result:
                    result[info["hash"]] = (0, 0)

        return result

    def _lookup_offsets(
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
            with Database() as db:
                # First try by qb_hash in Torrent table (most reliable for existing torrents)
                torrent_record = db.torrent.search_by_qb_hash(torrent_hash)
                if torrent_record and torrent_record.bangumi_id:
                    bangumi = db.bangumi.search_id(torrent_record.bangumi_id)
                    if bangumi and not bangumi.deleted:
                        logger.debug(
                            f"[Renamer] Found offsets via qb_hash: ep={bangumi.episode_offset}, season={bangumi.season_offset}"
                        )
                        return bangumi.episode_offset, bangumi.season_offset

                # Then try by bangumi_id from tags (for newly added torrents)
                bangumi_id = self._parse_bangumi_id_from_tags(tags)
                if bangumi_id:
                    bangumi = db.bangumi.search_id(bangumi_id)
                    if bangumi and not bangumi.deleted:
                        logger.debug(
                            f"[Renamer] Found offsets via tag ab:{bangumi_id}: ep={bangumi.episode_offset}, season={bangumi.season_offset}"
                        )
                        return bangumi.episode_offset, bangumi.season_offset

                # Then try matching by torrent name
                bangumi = db.bangumi.match_torrent(torrent_name)
                if bangumi:
                    logger.info(
                        f"[Renamer] Matched bangumi '{bangumi.official_title}' (id={bangumi.id}) via name, "
                        f"offsets: ep={bangumi.episode_offset}, season={bangumi.season_offset}"
                    )
                    return bangumi.episode_offset, bangumi.season_offset

                # Finally fall back to save_path matching with normalization
                normalized_save_path = self._normalize_path(save_path)
                bangumi = db.bangumi.match_by_save_path(save_path)
                if not bangumi:
                    # Try with normalized path if exact match failed
                    bangumi = db.bangumi.match_by_save_path(normalized_save_path)
                if bangumi:
                    logger.info(
                        f"[Renamer] Matched bangumi '{bangumi.official_title}' (id={bangumi.id}) via save_path, "
                        f"offsets: ep={bangumi.episode_offset}, season={bangumi.season_offset}"
                    )
                    return bangumi.episode_offset, bangumi.season_offset

                logger.info(
                    f"[Renamer] No bangumi match for torrent (using offset=0): "
                    f"name={torrent_name[:60] if torrent_name else 'N/A'}..."
                )
        except Exception as e:
            logger.debug(f"[Renamer] Could not lookup offsets for {save_path}: {e}")
        return 0, 0

    async def rename(self) -> list[Notification]:
        # Get torrent info
        logger.debug("[Renamer] Start rename process.")
        rename_method = settings.bangumi_manage.rename_method
        torrents_info = await self.get_torrent_info()
        renamed_info: list[Notification] = []
        # Fetch all torrent files concurrently
        all_files = await asyncio.gather(
            *[self.get_torrent_files(info["hash"]) for info in torrents_info]
        )
        # Batch lookup all offsets in a single database session
        offset_map = self._batch_lookup_offsets(torrents_info)
        for info, files in zip(torrents_info, all_files):
            torrent_hash = info["hash"]
            torrent_name = info["name"]
            save_path = info["save_path"]
            media_list, subtitle_list = self.check_files(files)
            bangumi_name, season = self._path_to_bangumi(save_path)
            # Use pre-fetched offsets
            episode_offset, season_offset = offset_map.get(torrent_hash, (0, 0))
            kwargs = {
                "torrent_name": torrent_name,
                "bangumi_name": bangumi_name,
                "method": rename_method,
                "season": season,
                "_hash": torrent_hash,
                "episode_offset": episode_offset,
                "season_offset": season_offset,
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
                logger.info("[Renamer] Start rename collection")
                await self.rename_collection(media_list=media_list, **kwargs)
                if len(subtitle_list) > 0:
                    await self.rename_subtitles(subtitle_list=subtitle_list, **kwargs)
                await self.set_category(torrent_hash, "BangumiCollection")
            else:
                logger.warning(f"[Renamer] {torrent_name} has no media file")
        logger.debug("[Renamer] Rename process finished.")
        return renamed_info

    def compare_ep_version(self, torrent_name: str, torrent_hash: str):
        if re.search(r"v\d.", torrent_name):
            pass
        else:
            self.delete_torrent(hashes=torrent_hash)
