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

    def tmdb_parser(self, title: str, season: int):
        official_title, tmdb_season = None, None
        try:
            tmdb_info = self._tmdb_parser.tmdb_search(title)
            logger.debug(f"TMDB Matched, official title is {tmdb_info.title_zh}")
        except Exception as e:
            logger.debug(e)
            logger.warning("Not Matched with TMDB")
            return title, season
        if settings.language == "zh":
            official_title = f"{tmdb_info.title_zh} ({tmdb_info.year_number})"
        elif settings.language == "jp":
            official_title = f"{tmdb_info.title_jp} ({tmdb_info.year_number})"
        tmdb_season = tmdb_info.last_season if tmdb_info.last_season else season
        official_title = official_title if official_title else title
        return official_title, tmdb_season

    def return_dict(self, _raw: str):
        try:
            episode = self.raw_parser(_raw)
            title_search = episode.title_zh if episode.title_zh else episode.title_en
            title_raw = episode.title_en if episode.title_en else episode.title_zh
            if settings.enable_tmdb:
                official_title, _season = self.tmdb_parser(title_search, episode.season)
            else:
                official_title = title_search if settings.language == "zh" else title_raw
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
                "eps_collect": True if episode.episode > 1 else False,
            }
            logger.debug(f"RAW:{_raw} >> {episode.title_en}")
            return data
        except Exception as e:
            logger.debug(e)


if __name__ == '__main__':
    import re
    from conf.const_dev import DEV_SETTINGS
    settings.init(DEV_SETTINGS)
    T = TitleParser()
    raw = "[梦蓝字幕组]New Doraemon 哆啦A梦新番[716][2022.07.23][AVC][10080P][GB_JP]"
    season = int(re.search(r"\d{1,2}", "S02").group())
    _dict = T.return_dict(raw)
    print(_dict)
