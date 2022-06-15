import logging

from parser.analyser import RawParser, DownloadParser, TMDBMatcher
from conf import settings

logger = logging.getLogger(__name__)


class TitleParser:
    def __init__(self):
        self._raw_parser = RawParser()
        self._download_parser = DownloadParser()

    def raw_parser(self, raw):
        return self._raw_parser.analyse(raw)

    def download_parser(self, download_raw, season, method=settings.method):
        return self._download_parser.download_rename(download_raw, season, method)

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