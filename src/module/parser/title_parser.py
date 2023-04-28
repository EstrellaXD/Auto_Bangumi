import logging

from .analyser import raw_parser, torrent_parser, TMDBMatcher

from module.conf import settings
from module.models import BangumiData

logger = logging.getLogger(__name__)
LANGUAGE = settings.rss_parser.language


class TitleParser:
    def __init__(self):
        self._tmdb_parser = TMDBMatcher()

    @staticmethod
    def torrent_parser(
            download_raw: str,
            folder_name: str | None = None,
            season: int | None = None,
            suffix: str | None = None,
            method: str = settings.bangumi_manage.rename_method
    ):
        return torrent_parser(download_raw, folder_name, season, suffix, method)

    def tmdb_parser(self, title: str, season: int):

        official_title, tmdb_season = None, None
        try:
            tmdb_info = self._tmdb_parser.tmdb_search(title)
            logger.debug(f"TMDB Matched, official title is {tmdb_info.title_zh}")
        except Exception as e:
            logger.debug(e)
            logger.warning(f"{title} can not Matched with TMDB")
            logger.info("Please change the bangumi info in webui")
            return title, season
        if LANGUAGE == "zh":
            official_title = f"{tmdb_info.title_zh} ({tmdb_info.year_number})"
        elif LANGUAGE == "jp":
            official_title = f"{tmdb_info.title_jp} ({tmdb_info.year_number})"
        tmdb_season = tmdb_info.last_season if tmdb_info.last_season else season
        official_title = official_title if official_title else title
        return official_title, tmdb_season

    def raw_parser(self, raw: str, _id: int | None = None) -> BangumiData:
        try:
            episode = raw_parser(raw)
            titles = {
                "zh": episode.title_zh,
                "en": episode.title_en,
                "jp": episode.title_jp
            }
            title_search = episode.title_zh if episode.title_zh else episode.title_en
            title_raw = episode.title_en if episode.title_en else episode.title_zh
            if settings.rss_parser.enable_tmdb:
                official_title, _season = self.tmdb_parser(title_search, episode.season)
            else:
                official_title = titles[LANGUAGE] if titles[LANGUAGE] else titles["zh"]
                _season = episode.season
            data = BangumiData(
                id=_id,
                official_title=official_title,
                title_raw=title_raw,
                season=_season,
                season_raw=episode.season_raw,
                group=episode.group,
                dpi=episode.resolution,
                source=episode.source,
                subtitle=episode.sub,
                added=False,
                eps_collect=True if episode.episode > 1 else False,
                offset=0,
                filter=settings.rss_parser.filter
            )
            logger.debug(f"RAW:{raw} >> {episode.title_en}")
            return data
        except Exception as e:
            logger.debug(e)
            print(e)
