import logging
import os.path
import re
from pathlib import PurePath, PureWindowsPath

from module.core.download_client import DownloadClient

from module.parser import TitleParser
from module.network import PostNotification
from module.models import Config

logger = logging.getLogger(__name__)


class Renamer:
    def __init__(self, download_client: DownloadClient, settings: Config):
        self._client = download_client
        self._renamer = TitleParser()
        self._notification = PostNotification()
        self.settings = settings

    @staticmethod
    def print_result(torrent_count, rename_count):
        if rename_count != 0:
            logger.info(
                f"Finished checking {torrent_count} files' name, renamed {rename_count} files."
            )
        logger.debug(f"Checked {torrent_count} files")

    def get_torrent_info(self, category="Bangumi"):
        recent_info = self._client.get_torrent_info(category=category)
        torrent_count = len(recent_info)
        return recent_info, torrent_count

    @staticmethod
    def check_files(info):
        media_list = []
        subtitle_list = []
        for f in info.files:
            file_name = f.name
            suffix = os.path.splitext(file_name)[-1]
            if suffix.lower() in [".mp4", ".mkv"]:
                media_list.append(file_name)
            elif suffix.lower() in [".ass", ".srt"]:
                subtitle_list.append(file_name)
        return media_list, subtitle_list

    def rename_file(
        self,
        info,
        media_path: str,
        method: str,
        bangumi_name: str,
        season: int,
        remove_bad_torrents: bool,
    ):
        torrent_name = info.name
        suffix = os.path.splitext(media_path)[-1]
        compare_name = self.get_file_name(media_path)
        new_path = self._renamer.torrent_parser(
            torrent_name=torrent_name,
            bangumi_name=bangumi_name,
            season=season,
            suffix=suffix,
            method=method,
        )
        if compare_name != new_path:
            try:
                self._client.rename_torrent_file(
                    _hash=info.hash, old_path=media_path, new_path=new_path
                )
                self._notification.send_msg(bangumi_name, f"{new_path}已经更新，已自动重命名。")
            except Exception as e:
                logger.warning(f"{torrent_name} rename failed")
                logger.warning(
                    f"Season name: {bangumi_name}, Season: {season}, Suffix: {suffix}"
                )
                logger.debug(e)
                # Delete bad torrent
                self.delete_bad_torrent(info, remove_bad_torrents)

    def rename_collection(
        self,
        info,
        media_list: list[str],
        bangumi_name: str,
        season: int,
        remove_bad_torrents: bool,
        method: str,
    ):
        _hash = info.hash
        for media_path in media_list:
            path_len = len(media_path.split(os.path.sep))
            if path_len <= 2:
                suffix = os.path.splitext(media_path)[-1]
                torrent_name = self.get_file_name(media_path)
                new_name = self._renamer.torrent_parser(
                    torrent_name=torrent_name,
                    bangumi_name=bangumi_name,
                    season=season,
                    suffix=suffix,
                    method=method,
                )
                if torrent_name != new_name:
                    try:
                        self._client.rename_torrent_file(
                            _hash=_hash, old_path=media_path, new_path=new_name
                        )
                    except Exception as e:
                        logger.warning(f"{torrent_name} rename failed")
                        logger.warning(
                            f"Bangumi name: {bangumi_name}, Season: {season}, Suffix: {suffix}"
                        )
                        logger.debug(e)
                        # Delete bad torrent.
                        self.delete_bad_torrent(info, remove_bad_torrents)
        self._client.set_category(category="BangumiCollection", hashes=_hash)

    def rename_subtitles(
        self,
        subtitle_list: list[str],
        bangumi_name: str,
        season: int,
        method: str,
        _hash,
    ):
        method = "subtitle_" + method
        for subtitle_path in subtitle_list:
            suffix = os.path.splitext(subtitle_path)[-1]
            old_name = self.get_file_name(subtitle_path)
            new_name = self._renamer.torrent_parser(
                method=method,
                torrent_name=old_name,
                bangumi_name=bangumi_name,
                season=season,
                suffix=suffix,
            )
            if old_name != new_name:
                try:
                    self._client.rename_torrent_file(
                        _hash=_hash, old_path=subtitle_path, new_path=new_name
                    )
                except Exception as e:
                    logger.warning(f"{old_name} rename failed")
                    logger.warning(f"Suffix: {suffix}")
                    logger.debug(e)

    def delete_bad_torrent(self, info, remove_bad_torrent: bool):
        if remove_bad_torrent:
            self._client.delete_torrent(info.hash)
            logger.info(f"{info.name} have been deleted.")

    @staticmethod
    def get_season_info(save_path: str, download_path: str):
        # Remove default save path
        save_path = save_path.replace(download_path, "")
        # Check windows or linux path
        path_parts = (
            PurePath(save_path).parts
            if PurePath(save_path).name != save_path
            else PureWindowsPath(save_path).parts
        )
        # Get folder name
        folder_name = (
            path_parts[1]
            if path_parts[0] == "/" or path_parts[0] == "\\"
            else path_parts[0]
        )
        # Get season
        try:
            if re.search(r"S\d{1,2}|[Ss]eason", path_parts[-1]) is not None:
                season = int(re.search(r"\d{1,2}", path_parts[-1]).group())
            else:
                season = 1
        except Exception as e:
            logger.debug(e)
            logger.debug("No Season info")
            season = 1
        return folder_name, season

    @staticmethod
    def get_file_name(file_path: str):
        # Check windows or linux path
        path_parts = (
            PurePath(file_path).parts
            if PurePath(file_path).name != file_path
            else PureWindowsPath(file_path).parts
        )
        # Get file name
        file_name = path_parts[-1]
        return file_name

    def rename(self):
        # Get torrent info
        download_path = self.settings.downloader.path
        rename_method = self.settings.bangumi_manage.rename_method
        remove_bad_torrents = self.settings.bangumi_manage.remove_bad_torrent
        recent_info, torrent_count = self.get_torrent_info()
        for info in recent_info:
            media_list, subtitle_list = self.check_files(info)
            bangumi_name, season = self.get_season_info(info.save_path, download_path)
            if len(media_list) == 1:
                self.rename_file(
                    info=info,
                    media_path=media_list[0],
                    method=rename_method,
                    bangumi_name=bangumi_name,
                    season=season,
                    remove_bad_torrents=remove_bad_torrents,
                )
                if len(subtitle_list) > 0:
                    self.rename_subtitles(
                        subtitle_list=subtitle_list,
                        bangumi_name=bangumi_name,
                        season=season,
                        method=rename_method,
                        _hash=info.hash,
                    )
            elif len(media_list) > 1:
                logger.info("Start rename collection")
                self.rename_collection(
                    info=info,
                    media_list=media_list,
                    bangumi_name=bangumi_name,
                    season=season,
                    remove_bad_torrents=remove_bad_torrents,
                    method=rename_method,
                )
                if len(subtitle_list) > 0:
                    self.rename_subtitles(
                        subtitle_list=subtitle_list,
                        bangumi_name=bangumi_name,
                        season=season,
                        method=rename_method,
                        _hash=info.hash,
                    )
            else:
                logger.warning(f"{info.name} has no media file")
