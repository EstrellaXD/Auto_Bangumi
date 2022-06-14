import logging

from parser.analyser.raw_parser import RawParser
from parser.analyser.rename_parser import DownloadEPParser
from parser.analyser.tmdb import TMDBMatcher

from conf.conf import settings

logger = logging.getLogger(__name__)


class TitleParser:
    def __init__(self):
        self._raw_parser = RawParser()
        self._download_parser = DownloadEPParser()

    def raw_parser(self, raw):
        return self._raw_parser.analyse(raw)

    def download_parser(self, download_raw, method=settings.method):
        return self._download_parser.download_rename(download_raw, method)

    def return_dict(self, raw):
        tmdb = TMDBMatcher()
        episode = self.raw_parser(raw)
        try:
            tmdb_info = tmdb.tmdb_search(episode.title)
            official_title = tmdb_info.title_zh if settings.zh_title else tmdb_info.title_jp
            season = tmdb_info.last_season
        except Exception as e:
            logger.debug(e)
            logger.info("Not Match in TMDB")
            official_title = episode.title
            season = episode.season_info.number
        data = {
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
        return data

if __name__ == "__main__":
    raw = "[Lilith-Raws] Love Live！虹咲学园 学园偶像同好会 S02 - 11 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4] "
    p = TitleParser()
    print(p.return_dict(raw))