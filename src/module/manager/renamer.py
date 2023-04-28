import logging
import os.path
import re
from pathlib import PurePath, PureWindowsPath

from module.core.download_client import DownloadClient

from module.conf import settings
from module.parser import TitleParser
from module.network import PostNotification

logger = logging.getLogger(__name__)


class Renamer:
    def __init__(self, download_client: DownloadClient):
        self.client = download_client
        self._renamer = TitleParser()
        self.notification = PostNotification()

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

    def rename_file(self, info, media_path):
        old_name = info.name
        suffix = os.path.splitext(media_path)[-1]
        compare_name = media_path.split(os.path.sep)[-1]
        folder_name, season = self.get_folder_and_season(info.save_path)
        new_path = self._renamer.download_parser(old_name, folder_name, season, suffix)
        if compare_name != new_path:
            try:
                self.client.rename_torrent_file(_hash=info.hash, old_path=media_path, new_path=new_path)
                self.notification.send_msg(folder_name, "update")
            except Exception as e:
                logger.warning(f"{old_name} rename failed")
                logger.warning(f"Folder name: {folder_name}, Season: {season}, Suffix: {suffix}")
                logger.debug(e)
                # Delete bad torrent
                self.delete_bad_torrent(info)

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
                        # Delete bad torrent.
                        self.delete_bad_torrent(info)
        self.client.set_category(category="BangumiCollection", hashes=_hash)

    def rename_subtitles(self, subtitle_list: list[str], media_old_name, media_new_name, _hash):
        for subtitle_file in subtitle_list:
            if re.search(media_old_name, subtitle_file) is not None:
                subtitle_lang = subtitle_file.split(".")[-2]
                new_subtitle_name = f"{media_new_name}.{subtitle_lang}.ass"
                self.client.rename_torrent_file(_hash, subtitle_file, new_subtitle_name)
                logger.info(f"Rename subtitles for {media_old_name} to {media_new_name}")

    def delete_bad_torrent(self, info):
        if settings.bangumi_manage.remove_bad_torrent:
            self.client.delete_torrent(info.hash)
            logger.info(f"{info.name} have been deleted.")

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


if __name__ == '__main__':
    client = DownloadClient()
    rn = Renamer(client)
    rn.rename()

