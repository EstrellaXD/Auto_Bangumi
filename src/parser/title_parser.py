import logging

from parser.analyser import RawParser, DownloadParser, TMDBMatcher
from conf import settings

logger = logging.getLogger(__name__)


class TitleParser:
    def __init__(self):
        self._raw_parser = RawParser()
        self._download_parser = DownloadParser()
        self._tmdb_parser = TMDBMatcher()

    def raw_parser(self, raw: str):
        return self._raw_parser.analyse(raw)

    def download_parser(self, download_raw, folder_name, season, suffix, method=settings.method):
        return self._download_parser.download_rename(download_raw, folder_name, season, suffix, method)

    def tmdb_parser(self, title: str, season:int):
        try:
            tmdb_info = self._tmdb_parser.tmdb_search(title)
            logger.debug(f"TMDB Matched, title is {tmdb_info.title_zh}")
        except Exception as e:
            logger.warning("Not Matched with TMDB")
            return title, season
        if settings.title_language == "zh":
            official_title = f"{tmdb_info.title_zh}({tmdb_info.year_number})"
        elif settings.title_language == "jp":
            official_title = f"{tmdb_info.title_jp}({tmdb_info.year_number})"
        season = tmdb_info.last_season
        return official_title, season

    def return_dict(self, raw: str):
        try:
            episode = self.raw_parser(raw)
            if settings.enable_tmdb:
                official_title, season = self.tmdb_parser(episode.title, episode.season_info.number)
            else:
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
                "eps_collect": True if settings.eps_complete and episode.ep_info.number > 1 else False,
            }
            logger.debug(f"RAW:{raw} >> {episode.title}")
            return data
        except Exception as e:
            logger.debug(e)


if __name__ == '__main__':
    import re
    from conf.const_dev import DEV_SETTINGS
    settings.init(DEV_SETTINGS)
    T = TitleParser()
    raw = "[SWSUB][7月新番][继母的拖油瓶是我的前女友/継母の连れ子が元カノだった][001][GB_JP][AVC][1080P][网盘][无修正] [331.6MB] [复制磁连]"
    season = int(re.search(r"\d{1,2}", "S02").group())
    dict = T.return_dict(raw)
    print(dict)
