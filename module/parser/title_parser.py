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

    def download_parser(self, download_raw, folder_name, season, suffix, offset_episode,
                        episode_count, method=settings.bangumi_manage.method):
        return self._download_parser.download_rename(download_raw, folder_name, season, suffix, offset_episode,
                                                     episode_count, method)

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
        tmdb_season = season
        official_title = official_title if official_title else title
        offset_episode = 0
        # 只处理文件名的season比tmdb最新season小1的情况
        if tmdb_info.last_season > 0 and tmdb_info.episode_count > 0 \
                and -1 == tmdb_info.last_season - season:
            offset_episode = int(tmdb_info.episode_count / 2)
            tmdb_season = tmdb_info.last_season
        return official_title, tmdb_season, offset_episode, tmdb_info.episode_count

    def return_dict(self, _raw: str):
        try:
            episode = self.raw_parser(_raw)
            title_search = episode.title_zh if episode.title_zh else episode.title_en
            title_raw = episode.title_en if episode.title_en else episode.title_zh
            if settings.rss_parser.enable_tmdb:
                official_title, _season, offset_episode, episode_count = self.tmdb_parser(title_search, episode.season)
            else:
                official_title = title_search if LANGUAGE == "zh" else title_raw
                _season = episode.season
                offset_episode, episode_count = 0
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
                "offset_episode": offset_episode,
                "episode_count": episode_count
            }
            logger.debug(f"RAW:{_raw} >> {episode.title_en}")
            return data
        except Exception as e:
            logger.debug(e)