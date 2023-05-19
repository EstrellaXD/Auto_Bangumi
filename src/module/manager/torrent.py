import logging

from module.downloader import DownloadClient
from module.conf import settings
from module.models import BangumiData


logger = logging.getLogger(__name__)


class TorrentManager(DownloadClient):
    def __match_torrents_list(self, data: BangumiData) -> list:
        torrents = self.get_torrent_info()
        matched_list = []
        for torrent in torrents:
            save_path = torrent.save_path
            bangumi_name, season = self._path_to_bangumi(save_path)
            if data.official_title in bangumi_name and data.season == season:
                matched_list.append(torrent.hash)
        return matched_list

    def delete_bangumi(self, data: BangumiData):
        hash_list = self.__match_torrents_list(data)
        self.delete_torrent(hash_list)

    def delete_rule(self, data: BangumiData):
        rule_name = f"{data.official_title}({data.year})" if data.year else data.title_raw
        if settings.bangumi_manage.group_tag:
            rule_name = f"[{data.group_name}] {rule_name}"
        self.remove_rule(rule_name)

    def set_new_path(self, data: BangumiData):
        # set download rule
        self.set_rule(data)
        # set torrent path
        match_list = self.__match_torrents_list(data)
        path = self._gen_save_path(data)
        self.move_torrent(match_list, path)
