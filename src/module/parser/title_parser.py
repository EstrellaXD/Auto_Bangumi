import logging

from .analyser import RawParser, DownloadParser, TMDBMatcher

from module.conf import settings

logger = logging.getLogger(__name__)
LANGUAGE = settings.rss_parser.language


class TitleParser:
    def __init__(self):
        self._raw_parser = RawParser()
        self._download_parser = DownloadParser()
        self._tmdb_parser = TMDBMatcher()

    def raw_parser(self, raw: str):
        return self._raw_parser.analyse(raw)

    def download_parser(self, download_raw, folder_name, season, suffix, method=settings.bangumi_manage.method):
        return self._download_parser.download_rename(download_raw, folder_name, season, suffix, method)

    def tmdb_parser(self, title: str, season: int):

        official_title, tmdb_season = None, None
        try:
            tmdb_info = self._tmdb_parser.tmdb_search(title)
            logger.debug(f"TMDB Matched, official title is {tmdb_info.title_zh}")
        except Exception as e:
            logger.debug(e)
            logger.warning("Not Matched with TMDB")
            return title, season
        if LANGUAGE == "zh":
            official_title = f"{tmdb_info.title_zh} ({tmdb_info.year_number})"
        elif LANGUAGE == "jp":
            official_title = f"{tmdb_info.title_jp} ({tmdb_info.year_number})"
        tmdb_season = tmdb_info.last_season if tmdb_info.last_season else season
        official_title = official_title if official_title else title
        return official_title, tmdb_season

    def return_dict(self, _raw: str):
        try:
            episode = self.raw_parser(_raw)
            title_search = episode.title_zh if episode.title_zh else episode.title_en
            title_raw = episode.title_en if episode.title_en else episode.title_zh
            if settings.rss_parser.enable_tmdb:
                official_title, _season = self.tmdb_parser(title_search, episode.season)
            else:
                official_title = title_search if LANGUAGE == "zh" else title_raw
                _season = episode.season
            data = {
                "official_title": official_title,
                "title_raw": title_raw,
                "season": _season,
                "season_raw": episode.season_raw,
                "group": episode.group,
                "dpi": episode.resolution,
                "source": episode.source,
                "subtitle": episode.sub,
                "added": False,
                "eps_collect": settings.bangumi_manage.eps_complete,
            }
            logger.debug(f"RAW:{_raw} >> {episode.title_en}")
            return data
        except Exception as e:
            logger.debug(e)