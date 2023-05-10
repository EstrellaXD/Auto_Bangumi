import logging

from module.downloader import DownloadClient
from module.conf import settings
from module.models import BangumiData

logger = logging.getLogger(__name__)


class TorrentManager(DownloadClient):
    @staticmethod
    def __gen_path(data: BangumiData):
        download_path = settings.downloader.path
        if ":\\" in download_path:
            import ntpath as path
        else:
            import os.path as path
        folder = f"{data.official_title}({data.year})" if data.year else data.official_title
        path = path.join(download_path, folder, f"Season {data.season}")
        return path

    @staticmethod
    def __match_torrents_list(title_raw: str) -> list:
        with DownloadClient() as client:
            torrents = client.get_torrent_info()
        return [torrent.hash for torrent in torrents if title_raw in torrent.name]

    def delete_bangumi(self, data: BangumiData):
        hash_list = self.__match_torrents_list(data.title_raw)
        self.delete_torrent(hash_list)

    def delete_rule(self, data: BangumiData):
        rule_name = f"{data.official_title}({data.year})" if data.year else data.title_raw
        if settings.bangumi_manage.group_tag:
            rule_name = f"[{data.group_name}] {rule_name}" if self.group_tag else rule_name
        self.remove_rule(rule_name)

    def set_new_path(self, data: BangumiData):
        # set download rule
        self.set_rule(data)
        # set torrent path
        match_list = self.__match_torrents_list(data.title_raw)
        path = self.__gen_path(data)
        self.move_torrent(match_list, path)
