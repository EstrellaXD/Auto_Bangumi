import logging
import os.path
import re
from pathlib import PurePath, PureWindowsPath

from module.core.download_client import DownloadClient

from module.conf import settings
from module.parser import TitleParser

logger = logging.getLogger(__name__)


class Renamer:
    def __init__(self, download_client: DownloadClient):
        self.client = download_client
        self._renamer = TitleParser()

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
    def split_path(path: str):
        suffix = os.path.splitext(path)[-1]
        path = path.replace(settings.downloader.path, "")
        path_parts = PurePath(path).parts \
            if PurePath(path).name != path \
            else PureWindowsPath(path).parts
        path_name = path_parts[-1]
        try:
            if re.search(r"S\d{1,2}|[Ss]eason", path_parts[-2]) is not None:
                season = int(re.search(r"\d{1,2}", path_parts[-2]).group())
            else:
                season = 1
        except Exception as e:
            logger.debug(e)
            logger.debug("No Season info")
            season = 1
        folder_name = path_parts[1] if path_parts[0] == "/" else path_parts[0]
        try:
            download_path = path_parts[1]
        except IndexError:
            download_path = ""
        return path_name, season, folder_name, suffix, download_path

    def run(self):
        recent_info, torrent_count = self.get_torrent_info()
        rename_count = 0
        for info in recent_info:
            name = info.name
            torrent_hash = info.hash
            path_name, season, folder_name, suffix, _ = self.split_path(info.content_path)
            if path_name is folder_name:
                logger.warning("Wrong bangumi path, please check your qbittorrent settings.")
            else:
                try:
                    new_name = self._renamer.download_parser(name, folder_name, season, suffix, settings.bangumi_manage.rename_method)
                    if path_name != new_name:
                        old_path = info.content_path.replace(info.save_path, "")[len(os.path.sep):]
                        self.client.rename_torrent_file(torrent_hash, old_path, new_name)
                        rename_count += 1
                    else:
                        continue
                except Exception as e:
                    logger.warning(f"{path_name} rename failed")
                    logger.warning(f"Folder name: {folder_name}, Season: {season}, Suffix: {suffix}")
                    logger.debug(e)
                    if settings.bangumi_manage.remove_bad_torrent:
                        self.client.delete_torrent(torrent_hash)
        self.print_result(torrent_count, rename_count)

    def set_folder(self):
        recent_info, _ = self.get_torrent_info()
        for info in recent_info:
            torrent_hash = info.hash
            _, season, folder_name, _, download_path = self.split_path(info.content_path)
            new_path = os.path.join(settings.downloader.path, folder_name, f"Season {season}")
            self.client.move_torrent(torrent_hash, new_path)

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
            if suffix in suffix_list:
                file_list.append(file_name)
        return file_list

    def rename_file(self, info, media_path):
        old_name = info.name
        suffix = os.path.splitext(media_path)[-1]
        compare_name = media_path.split(os.path.sep)[-1]
        folder_name, season = self.get_folder_and_season(info.save_path)
        new_path = self._renamer.download_parser(old_name, folder_name, season, suffix)
        if compare_name != new_path:
            try:
                self.client.rename_torrent_file(_hash=info.hash, old_path=media_path, new_path=new_path)
            except Exception as e:
                logger.warning(f"{old_name} rename failed")
                logger.warning(f"Folder name: {folder_name}, Season: {season}, Suffix: {suffix}")
                logger.debug(e)

    def rename_collection(self, info, media_list: list[str]):
        folder_name, season = self.get_folder_and_season(info.save_path)
        _hash = info.hash
        for media_path in media_list:
            path_len = len(media_path.split(os.path.sep))
            if path_len <= 2:
                suffix = os.path.splitext(media_path)[-1]
                old_name = media_path.split(os.path.sep)[-1]
                new_name = self._renamer.download_parser(old_name, folder_name, season, suffix)
                if old_name != new_name:
                    try:
                        self.client.rename_torrent_file(_hash=_hash, old_path=media_path, new_path=new_name)
                    except Exception as e:
                        logger.warning(f"{old_name} rename failed")
                        logger.warning(f"Folder name: {folder_name}, Season: {season}, Suffix: {suffix}")
                        logger.debug(e)
        self.client.set_category(category="BangumiCollection", hashes=_hash)

    def rename_subtitles(self, subtitle_list: list[str], media_old_name, media_new_name, _hash):
        for subtitle_file in subtitle_list:
            if re.search(media_old_name, subtitle_file) is not None:
                subtitle_lang = subtitle_file.split(".")[-2]
                new_subtitle_name = f"{media_new_name}.{subtitle_lang}.ass"
                self.client.rename_torrent_file(_hash, subtitle_file, new_subtitle_name)
                logger.info(f"Rename subtitles for {media_old_name} to {media_new_name}")


    @staticmethod
    def get_folder_and_season(save_path: str):
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
            try:
                media_list = self.check_files(info)
                if len(media_list) == 1:
                    self.rename_file(info, media_list[0])
                    rename_count += 1
                # TODO: Rename subtitles
                elif len(media_list) > 1:
                    logger.info("Start rename collection")
                    self.rename_collection(info, media_list)
                    rename_count += len(media_list)
                else:
                    logger.warning(f"{info.name} has no media file")
            except Exception as e:
                logger.warning(f"{info.name} rename failed")
                logger.debug(e)
                if settings.bangumi_manage.remove_bad_torrent:
                    self.client.delete_torrent(info.hash)


if __name__ == '__main__':
    client = DownloadClient()
    rn = Renamer(client)
    rn.rename()

