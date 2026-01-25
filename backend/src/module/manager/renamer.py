import asyncio
import logging
import re

from module.conf import settings
from module.database import Database
from module.downloader import DownloadClient
from module.models import EpisodeFile, Notification, SubtitleFile
from module.parser import TitleParser

logger = logging.getLogger(__name__)


class Renamer(DownloadClient):
    def __init__(self):
        super().__init__()
        self._parser = TitleParser()
        self.check_pool = {}

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
            season_offset: int = 0,
    ) -> str:
        # Apply season offset
        adjusted_season = file_info.season + season_offset
        if adjusted_season < 1:
            adjusted_season = file_info.season  # Safety: don't go below 1
            logger.warning(f"[Renamer] Season offset {season_offset} would result in invalid season, ignoring")
        season = f"0{adjusted_season}" if adjusted_season < 10 else adjusted_season
        # Apply episode offset
        adjusted_episode = int(file_info.episode) + episode_offset
        if adjusted_episode < 1:
            adjusted_episode = int(file_info.episode)  # Safety: don't go below 1
            logger.warning(f"[Renamer] Episode offset {episode_offset} would result in negative episode, ignoring")
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
            new_path = self.gen_path(ep, bangumi_name, method=method, episode_offset=episode_offset, season_offset=season_offset)
            if media_path != new_path:
                if new_path not in self.check_pool.keys():
                    if await self.rename_torrent_file(
                        _hash=_hash, old_path=media_path, new_path=new_path
                    ):
                        # Return adjusted season and episode numbers for notification
                        adjusted_season = ep.season + season_offset
                        if adjusted_season < 1:
                            adjusted_season = ep.season
                        adjusted_episode = int(ep.episode) + episode_offset
                        if adjusted_episode < 1:
                            adjusted_episode = int(ep.episode)
                        return Notification(
                            official_title=bangumi_name,
                            season=adjusted_season,
                            episode=adjusted_episode,
                        )
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
                    new_path = self.gen_path(ep, bangumi_name, method=method, episode_offset=episode_offset, season_offset=season_offset)
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
                new_path = self.gen_path(sub, bangumi_name, method=method, episode_offset=episode_offset, season_offset=season_offset)
                if subtitle_path != new_path:
                    renamed = await self.rename_torrent_file(
                        _hash=_hash, old_path=subtitle_path, new_path=new_path
                    )
                    if not renamed:
                        logger.warning(f"[Renamer] {subtitle_path} rename failed")

    def _lookup_offsets_by_path(self, save_path: str) -> tuple[int, int]:
        """Look up episode and season offsets for a bangumi by its save_path.

        Returns:
            tuple[int, int]: (episode_offset, season_offset)
        """
        try:
            with Database() as db:
                bangumi = db.bangumi.match_by_save_path(save_path)
                if bangumi:
                    return bangumi.episode_offset, bangumi.season_offset
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
        for info, files in zip(torrents_info, all_files):
            torrent_hash = info["hash"]
            torrent_name = info["name"]
            save_path = info["save_path"]
            media_list, subtitle_list = self.check_files(files)
            bangumi_name, season = self._path_to_bangumi(save_path)
            # Look up offsets from database
            episode_offset, season_offset = self._lookup_offsets_by_path(save_path)
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
