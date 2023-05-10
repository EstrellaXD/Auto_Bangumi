import logging
import os.path
import re
from pathlib import PurePath, PureWindowsPath

from module.core.download_client import DownloadClient

from module.parser import TitleParser
from module.network import PostNotification
from module.models import SubtitleFile, EpisodeFile
from module.conf import settings

logger = logging.getLogger(__name__)


class Renamer(DownloadClient):
    def __init__(self):
        super().__init__()
        self._renamer = TitleParser()
        self._notification = PostNotification()

    @staticmethod
    def print_result(torrent_count, rename_count):
        if rename_count != 0:
            logger.info(
                f"Finished checking {torrent_count} files' name, renamed {rename_count} files."
            )
        logger.debug(f"Checked {torrent_count} files")

    def rename_info(self, category="Bangumi"):
        recent_info = self.get_torrent_info(category=category)
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

    @staticmethod
    def gen_path(file_info: EpisodeFile | SubtitleFile, bangumi_name: str, method: str) -> str:
        season = f"0{file_info.season}" if file_info.season < 10 else file_info.season
        episode = f"0{file_info.episode}" if file_info.episode < 10 else file_info.episode
        if method == "None":
            return file_info.media_path
        elif method == "pn":
            return f"{file_info.title} S{season}E{episode}{file_info.suffix}"
        elif method == "advance":
            return f"{bangumi_name} S{season}E{episode}{file_info.suffix}"
        elif method == "subtitle_pn":
            return f"{file_info.title} S{season}E{episode}.{file_info.language}{file_info.suffix}"
        elif method == "subtitle_advance":
            return f"{bangumi_name} S{season}E{episode}.{file_info.language}{file_info.suffix}"

    def rename_file(
        self,
        torrent_name: str,
        media_path: str,
        bangumi_name: str,
        method: str,
        season: int,
        _hash: str,
    ):
        ep = self._renamer.torrent_parser(
            torrent_name=torrent_name,
            torrent_path=media_path,
            season=season,
        )
        if ep:
            new_path = self.gen_path(ep, bangumi_name, method=method)
            if media_path != new_path:
                renamed = self.rename_torrent_file(_hash=_hash, old_path=media_path, new_path=new_path)
                if renamed:
                    if settings.notification.enable:
                        # self._notification.send_msg()
                        pass
                else:
                    logger.warning(f"{bangumi_name} Season {ep.season} Ep {ep.episode} rename failed.")
                    if settings.bangumi_manage.remove_bad_torrent:
                        self.delete_torrent(hashes=_hash)
        else:
            logger.warning(f"{media_path} parse failed")

    def rename_collection(
        self,
        info,
        media_list: list[str],
        bangumi_name: str,
        season: int,
        method: str,
    ):
        _hash = info.hash
        for media_path in media_list:
            path_len = len(media_path.split(os.path.sep))
            if path_len <= 2:
                ep = self._renamer.torrent_parser(
                    torrent_path=media_path,
                    season=season,
                )
                new_path = self.gen_path(ep, bangumi_name, method=method)
                if media_path != new_path:
                    renamed = self.rename_torrent_file(
                        _hash=_hash, old_path=media_path, new_path=new_path
                    )
                    if not renamed:
                        logger.warning(f"{media_path} rename failed")
                        # Delete bad torrent.
                        if settings.bangumi_manage.remove_bad_torrent:
                            self.delete_torrent(_hash)
                            break

    def rename_subtitles(
        self,
        subtitle_list: list[str],
        torrent_name: str,
        bangumi_name: str,
        season: int,
        method: str,
        _hash,
    ):
        method = "subtitle_" + method
        for subtitle_path in subtitle_list:
            sub = self._renamer.torrent_parser(
                torrent_path=subtitle_path,
                torrent_name=torrent_name,
                season=season,
            )
            new_path = self.gen_path(sub, bangumi_name, method=method)
            if subtitle_path != new_path:
                renamed = self.rename_torrent_file(
                    _hash=_hash, old_path=subtitle_path, new_path=new_path
                )
                if not renamed:
                    logger.warning(f"{subtitle_path} rename failed")

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
        download_path = settings.downloader.path
        rename_method = settings.bangumi_manage.rename_method
        recent_info, torrent_count = self.rename_info()
        for info in recent_info:
            media_list, subtitle_list = self.check_files(info)
            bangumi_name, season = self.get_season_info(info.save_path, download_path)
            if len(media_list) == 1:
                self.rename_file(
                    media_path=media_list[0],
                    torrent_name=info.name,
                    method=rename_method,
                    bangumi_name=bangumi_name,
                    season=season,
                    _hash=info.hash,
                )
                if len(subtitle_list) > 0:
                    self.rename_subtitles(
                        subtitle_list=subtitle_list,
                        torrent_name=info.name,
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
                    method=rename_method,
                )
                if len(subtitle_list) > 0:
                    self.rename_subtitles(
                        subtitle_list=subtitle_list,
                        torrent_name=info.name,
                        bangumi_name=bangumi_name,
                        season=season,
                        method=rename_method,
                        _hash=info.hash,
                    )
            else:
                logger.warning(f"{info.name} has no media file")
