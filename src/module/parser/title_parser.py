import logging

from .analyser import raw_parser, torrent_parser, TMDBMatcher

from module.models import BangumiData, Config

logger = logging.getLogger(__name__)


class TitleParser:
    def __init__(self):
        self._tmdb_parser = TMDBMatcher()

    @staticmethod
    def torrent_parser(
        torrent_path: str,
        season: int | None = None,
    ):
        return torrent_parser(torrent_path, season)

    def tmdb_parser(self, title: str, season: int, language: str):
        official_title, tmdb_season = None, None
        try:
            tmdb_info = self._tmdb_parser.tmdb_search(title)
            logger.debug(f"TMDB Matched, official title is {tmdb_info.title_zh}")
        except Exception as e:
            logger.debug(e)
            logger.warning(f"{title} can not Matched with TMDB")
            logger.info("Please change the bangumi info in webui")
            return title, season
        if language == "zh":
            official_title = f"{tmdb_info.title_zh} ({tmdb_info.year_number})"
        elif language == "jp":
            official_title = f"{tmdb_info.title_jp} ({tmdb_info.year_number})"
        tmdb_season = tmdb_info.last_season if tmdb_info.last_season else season
        official_title = official_title if official_title else title
        return official_title, tmdb_season

    def raw_parser(self, raw: str, rss_link: str, settings: Config, _id: int = 0) -> BangumiData:
        language = settings.rss_parser.language
        try:
            episode = raw_parser(raw)
            titles = {
                "zh": episode.title_zh,
                "en": episode.title_en,
                "jp": episode.title_jp,
            }
            title_search = episode.title_zh if episode.title_zh else episode.title_en
            title_raw = episode.title_en if episode.title_en else episode.title_zh
            if settings.rss_parser.enable_tmdb:
                official_title, _season = self.tmdb_parser(
                    title_search, episode.season, language
                )
            else:
                official_title = titles[language] if titles[language] else titles["zh"]
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
                eps_collect=True if episode.episode > 1 else False,
                offset=0,
                filter=settings.rss_parser.filter,
                rss_link=[rss_link],
            )
            logger.debug(f"RAW:{raw} >> {episode.title_en}")
            return data
        except Exception as e:
            logger.debug(e)
            print(e)
