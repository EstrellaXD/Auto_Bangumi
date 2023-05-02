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
        self.client = download_client
        self._renamer = TitleParser()
        self.notification = PostNotification()
        self.settings = settings

    @staticmethod
    def print_result(torrent_count, rename_count):
        if rename_count != 0:
            logger.info(f"Finished checking {torrent_count} files' name, renamed {rename_count} files.")
        logger.debug(f"Checked {torrent_count} files")

    def get_torrent_info(self, category="Bangumi"):
        recent_info = self.client.get_torrent_info(category=category)
        torrent_count = len(recent_info)
        return recent_info, torrent_count

    @staticmethod
    def check_files(info, suffix_type: str = "media"):
        if suffix_type == "subtitle":
            suffix_list = [".ass", ".srt"]
        else:
            suffix_list = [".mp4", ".mkv"]
        file_list = []
        for f in info.files:
            file_name = f.name
            suffix = os.path.splitext(file_name)[-1]
            if suffix.lower() in suffix_list:
                file_list.append(file_name)
        return file_list

    def rename_file(self, info, media_path: str, settings: Config):
        torrent_name = info.name
        suffix = os.path.splitext(media_path)[-1]
        compare_name = media_path.split(os.path.sep)[-1]
        bangumi_name, season = self.get_season_info(info.save_path, settings)
        new_path = self._renamer.torrent_parser(
            torrent_name=torrent_name,
            bangumi_name=bangumi_name,
            season=season,
            suffix=suffix,
            method=settings.bangumi_manage.rename_method
        )
        if compare_name != new_path:
            try:
                self.client.rename_torrent_file(_hash=info.hash, old_path=media_path, new_path=new_path)
                self.notification.send_msg(bangumi_name, "update")
            except Exception as e:
                logger.warning(f"{torrent_name} rename failed")
                logger.warning(f"Season name: {bangumi_name}, Season: {season}, Suffix: {suffix}")
                logger.debug(e)
                # Delete bad torrent
                self.delete_bad_torrent(info, settings)

    def rename_collection(self, info, media_list: list[str], settings: Config):
        bangumi_name, season = self.get_season_info(info.save_path, settings)
        _hash = info.hash
        for media_path in media_list:
            path_len = len(media_path.split(os.path.sep))
            if path_len <= 2:
                suffix = os.path.splitext(media_path)[-1]
                torrent_name = media_path.split(os.path.sep)[-1]
                new_name = self._renamer.torrent_parser(
                    torrent_name=torrent_name,
                    bangumi_name=bangumi_name,
                    season=season,
                    suffix=suffix,
                    method=settings.bangumi_manage.rename_method
                )
                if torrent_name != new_name:
                    try:
                        self.client.rename_torrent_file(_hash=_hash, old_path=media_path, new_path=new_name)
                    except Exception as e:
                        logger.warning(f"{torrent_name} rename failed")
                        logger.warning(f"Bangumi name: {bangumi_name}, Season: {season}, Suffix: {suffix}")
                        logger.debug(e)
                        # Delete bad torrent.
                        self.delete_bad_torrent(info, settings)
        self.client.set_category(category="BangumiCollection", hashes=_hash)

    def rename_subtitles(self, subtitle_list: list[str], _hash):
        for subtitle_path in subtitle_list:
            suffix = os.path.splitext(subtitle_path)[-1]
            old_name = subtitle_path.split(os.path.sep)[-1]
            new_name = self._renamer.torrent_parser(old_name, suffix)
            if old_name != new_name:
                try:
                    self.client.rename_torrent_file(_hash=_hash, old_path=subtitle_path, new_path=new_name)
                except Exception as e:
                    logger.warning(f"{old_name} rename failed")
                    logger.warning(f"Suffix: {suffix}")
                    logger.debug(e)

    def delete_bad_torrent(self, info, settings: Config):
        if settings.bangumi_manage.remove_bad_torrent:
            self.client.delete_torrent(info.hash)
            logger.info(f"{info.name} have been deleted.")

    @staticmethod
    def get_season_info(save_path: str, settings: Config):
        # Remove default save path
        save_path = save_path.replace(settings.downloader.path, "")
        # Check windows or linux path
        path_parts = PurePath(save_path).parts \
            if PurePath(save_path).name != save_path \
            else PureWindowsPath(save_path).parts
        # Get folder name
        folder_name = path_parts[1] if path_parts[0] == "/" else path_parts[0]
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

    def rename(self):
        # Get torrent info
        recent_info, torrent_count = self.get_torrent_info()
        rename_count = 0
        for info in recent_info:
            media_list = self.check_files(info)
            if len(media_list) == 1:
                self.rename_file(info, media_list[0], self.settings)
                rename_count += 1
            # TODO: Rename subtitles
            elif len(media_list) > 1:
                logger.info("Start rename collection")
                self.rename_collection(info, media_list, self.settings)
                rename_count += len(media_list)
            else:
                logger.warning(f"{info.name} has no media file")
