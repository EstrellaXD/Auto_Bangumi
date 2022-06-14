import logging

from parser.analyser.raw_parser import RawParser
from parser.analyser.rename_parser import DownloadEPParser
from parser.analyser.tmdb import TMDBinfo

from conf.conf import settings

logger = logging.getLogger(__name__)


class TitleParser:
    def __init__(self):
        self._raw_parser = RawParser()
        self._download_parser = DownloadEPParser()
        self.tmdb = TMDBinfo

    def raw_parser(self, raw):
        return self._raw_parser.analyse(raw)

    def download_parser(self, download_raw, method=settings.method):
        return self._download_parser.download_rename(download_raw, method)

    def return_dict(self, raw):
        episode = self.raw_parser(raw)
        try:
            tmdb_info = self.tmdb.tmdb_search(episode.title)
            official_title = tmdb_info.title_jp
            season = tmdb_info.last_season
        except Exception as e:
            logger.debug(e)
            logger.info("No data in TMDB")
            official_title = episode.title
            season = episode.season_info.raw
        return {
            "official_title": official_title,
            "title_raw": episode.title,
            "season": season,
            "season_raw": episode.season_info.raw,
            "group": episode.group,
            "dpi": episode.dpi,
            "source": episode.source,
            "subtitle": episode.subtitle,
            "added": False,
            "eps_collect": True if settings.eps_complete else False,
        }

if __name__ == "__main__":
    raw = "[离谱Sub] 朋友游戏 / トモダチゲーム / Tomodachi Game [10][AVC AAC][1080p][简体内嵌] [401.7MB]"
    p = TitleParser()
    print(p.return_dict(raw))