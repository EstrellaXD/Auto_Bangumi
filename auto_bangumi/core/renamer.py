import logging
import os.path
import re
import os.path
from pathlib import PurePath, PureWindowsPath


from conf import settings
from core import DownloadClient
from parser import TitleParser

logger = logging.getLogger(__name__)


class Renamer:
    def __init__(self, download_client: DownloadClient):
        self.client = download_client
        self._renamer = TitleParser()

    def print_result(self, torrent_count, rename_count):
        if rename_count != 0:
            logger.info(f"Finished checking {torrent_count} files' name, renamed {rename_count} files.")
        logger.debug(f"Checked {torrent_count} files")

    def get_torrent_info(self):
        recent_info = self.client.get_torrent_info()
        torrent_count = len(recent_info)
        return recent_info, torrent_count

    def split_path(self, path: str):
        suffix = os.path.splitext(path)[-1]
        path = path.replace(settings.download_path, "")
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

            try:
                new_name = self._renamer.download_parser(name, folder_name, season, suffix, settings.method)
                if path_name != new_name:
                    self.client.rename_torrent_file(torrent_hash, path_name, new_name)
                    rename_count += 1
                else:
                    continue
            except:
                logger.warning(f"{path_name} rename failed")
                if settings.remove_bad_torrent:
                    self.client.delete_torrent(torrent_hash)
        self.print_result(torrent_count, rename_count)

    def set_folder(self):
        recent_info, _ = self.get_torrent_info()
        for info in recent_info:
            torrent_hash = info.hash
            _, season, folder_name, _, download_path = self.split_path(info.content_path)
            new_path = os.path.join(settings.download_path, folder_name, f"Season {season}")
            # print(new_path)
            self.client.move_torrent(torrent_hash, new_path)


if __name__ == "__main__":
    from conf.const_dev import DEV_SETTINGS
    settings.init(DEV_SETTINGS)
    client = DownloadClient()
    rename = Renamer(client)
    rename.run()
    # rename.set_folder()
