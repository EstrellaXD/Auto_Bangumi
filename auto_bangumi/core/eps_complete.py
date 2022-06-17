import os.path
import re
import logging

from conf import settings
from network import RequestContent
from core import DownloadClient

logger = logging.getLogger(__name__)


class FullSeasonGet:
    def __init__(self):
        self._get_rss = RequestContent()

    def init_eps_complete_search_str(self, data: dict):
        search_str_pre = ""
        for i in [data['group'], data['title_raw'], data['season_raw'], data['subtitle'], data['source'], data['dpi']]:
            if i is not None:
                search_str_pre += f" {i}"
        search_str = re.sub(r"[\W_ ]", "+",
                            search_str_pre.strip())
        return search_str

    def get_season_torrents(self, data: dict):
        keyword = self.init_eps_complete_search_str(data)
        torrents = self._get_rss.get_torrents(f"https://mikanani.me/RSS/Search?searchstr={keyword}")
        return torrents

    def collect_season_torrents(self, data: dict):
        torrents = self.get_season_torrents(data)
        downloads = []
        for torrent in torrents:
            download_info = {
                "url": torrent,
                "save_path": os.path.join(
                        settings.download_path,
                        data["official_title"],
                        f"Season {data['season']}")
            }
            downloads.append(download_info)
        return downloads

    def eps_complete(self, bangumi_info, download_client: DownloadClient):
        for data in bangumi_info:
            if data["eps_collect"]:
                logger.info(f"Start collecting past episodes of {data['official_title']} Season {data['season']}...")
                downloads = self.collect_season_torrents(data)
                for download in downloads:
                    download_client.add_torrent(download)
                logger.info("Completed!")
                data["eps_collect"] = False


if __name__ == "__main__":
    a = FullSeasonGet()
    data = {
            "official_title": "指名！",
            "title_raw": "CUE!",
            "season": 1,
            "season_raw": "",
            "group": "喵萌Production",
            "dpi": "1080p",
            "source": None,
            "subtitle": "简日双语",
            "added": True,
            "eps_collect": True
        }
    torrents = a.collect_season_torrents(data)
    print(torrents)