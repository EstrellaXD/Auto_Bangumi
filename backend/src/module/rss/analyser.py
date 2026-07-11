import logging
import re

from module.conf import settings
from module.models import Bangumi, Movie, ResponseModel, RSSItem, Torrent
from module.network import RequestContent
from module.parser import TitleParser

from .engine import RSSEngine

logger = logging.getLogger(__name__)


class RSSAnalyser:
    async def official_title_parser_movie(
        self,
        movie: Movie,
        rss: RSSItem,
        torrent: Torrent,
        fetch_poster: bool = True,
    ):
        if not fetch_poster:
            pass
        elif rss.parser == "mikan":
            if not torrent.homepage:
                logger.warning("Mikan movie torrent has no homepage info.")
            else:
                try:
                    poster_link, official_title = await TitleParser.mikan_parser(
                        torrent.homepage
                    )
                except AttributeError as e:
                    logger.warning(
                        f"Failed to parse Mikan homepage {torrent.homepage}: {e}"
                    )
                else:
                    movie.poster_link = poster_link
                    if official_title:
                        movie.official_title = official_title
        elif rss.parser == "tmdb":
            tmdb_title, _, year, poster_link = await TitleParser.tmdb_parser(
                movie.official_title,
                1,
                settings.rss_parser.language,
                episode_type="movie",
            )
            movie.official_title = tmdb_title
            if year:
                try:
                    movie.year = int(year)
                except (ValueError, TypeError):
                    pass
            movie.poster_link = poster_link
        if movie.official_title:
            movie.official_title = re.sub(r"[/:.\\]", " ", movie.official_title)

    async def official_title_parser(
        self,
        bangumi: Bangumi,
        rss: RSSItem,
        torrent: Torrent,
        fetch_poster: bool = True,
    ):
        if not fetch_poster:
            pass
        elif rss.parser == "mikan":
            if not torrent.homepage:
                logger.warning("Mikan torrent has no homepage info.")
            else:
                try:
                    poster_link, official_title = await TitleParser.mikan_parser(
                        torrent.homepage
                    )
                except AttributeError as e:
                    logger.warning(
                        f"Failed to parse Mikan homepage " f"{torrent.homepage}: {e}"
                    )
                else:
                    bangumi.poster_link = poster_link
                    if official_title:
                        bangumi.official_title = official_title
        elif rss.parser == "tmdb":
            tmdb_title, season, year, poster_link = await TitleParser.tmdb_parser(
                bangumi.official_title,
                bangumi.season,
                settings.rss_parser.language,
                episode_type=bangumi.episode_type,
            )
            bangumi.official_title = tmdb_title
            bangumi.year = year
            bangumi.season = season
            bangumi.poster_link = poster_link
        else:
            pass
        if bangumi.official_title:
            bangumi.official_title = re.sub(r"[/:.\\]", " ", bangumi.official_title)

    @staticmethod
    async def get_rss_torrents(rss_link: str, full_parse: bool = True) -> list[Torrent]:
        async with RequestContent() as req:
            if full_parse:
                rss_torrents = await req.get_torrents(rss_link)
            else:
                rss_torrents = await req.get_torrents(rss_link, "\\d+-\\d+")
        return rss_torrents

    async def torrents_to_data(
        self, torrents: list[Torrent], rss: RSSItem, full_parse: bool = True
    ) -> tuple[list[Bangumi], list[Movie]]:
        new_bangumi: list[Bangumi] = []
        new_movies: list[Movie] = []
        seen_identities: set[tuple[str, str, int]] = set()
        for torrent in torrents:
            result = await TitleParser.raw_parser(raw=torrent.name)
            if result is None or not result.title_raw:
                continue
            title_raw = result.title_raw
            identity = (
                ("movie", title_raw, 0)
                if isinstance(result, Movie)
                else (result.episode_type, title_raw, result.season)
            )
            if identity in seen_identities:
                continue
            if isinstance(result, Movie):
                await self.official_title_parser_movie(
                    movie=result, rss=rss, torrent=torrent
                )
                result.rss_link = rss.url
                seen_identities.add(identity)
                new_movies.append(result)
                logger.info(f"New movie found: {result.official_title}")
            elif isinstance(result, Bangumi):
                await self.official_title_parser(
                    bangumi=result, rss=rss, torrent=torrent
                )
                result.rss_link = rss.url
                if not full_parse:
                    return [result], new_movies
                seen_identities.add(identity)
                new_bangumi.append(result)
                logger.info(f"New bangumi found: {result.official_title}")
        return new_bangumi, new_movies

    async def torrent_to_data(
        self, torrent: Torrent, rss: RSSItem, fetch_poster: bool = True
    ) -> Bangumi | Movie | None:
        result = await TitleParser.raw_parser(raw=torrent.name)
        if result:
            if isinstance(result, Movie):
                await self.official_title_parser_movie(
                    movie=result,
                    rss=rss,
                    torrent=torrent,
                    fetch_poster=fetch_poster,
                )
                result.rss_link = rss.url
            else:
                await self.official_title_parser(
                    bangumi=result,
                    rss=rss,
                    torrent=torrent,
                    fetch_poster=fetch_poster,
                )
                result.rss_link = rss.url
            return result
        return None

    async def rss_to_data(
        self, rss: RSSItem, engine: RSSEngine, full_parse: bool = True
    ) -> list[Bangumi]:
        rss_torrents = await self.get_rss_torrents(rss.url, full_parse)
        # Filter out already-known movies first
        torrents_after_movies = await engine.db.movie.match_list(rss_torrents, rss.url)
        # Then filter out already-known bangumi
        torrents_to_add = await engine.db.bangumi.match_list(
            torrents_after_movies, rss.url
        )
        if not torrents_to_add:
            logger.debug("No new title has been found.")
            return []
        # Parse remaining torrents
        new_bangumi, new_movies = await self.torrents_to_data(
            torrents_to_add, rss, full_parse
        )
        for movie in new_movies:
            await engine.db.movie.add(movie)
        if new_bangumi:
            await engine.db.bangumi.add_all(new_bangumi)
            return new_bangumi
        return []

    async def link_to_data(self, rss: RSSItem) -> Bangumi | Movie | ResponseModel:
        torrents = await self.get_rss_torrents(rss.url, False)
        if not torrents:
            return ResponseModel(
                status=False,
                status_code=406,
                msg_en="Cannot find any torrent.",
                msg_zh="无法找到种子。",
            )
        for torrent in torrents:
            data = await self.torrent_to_data(torrent, rss)
            if data:
                return data
        return ResponseModel(
            status=False,
            status_code=406,
            msg_en="Cannot parse this link.",
            msg_zh="无法解析此链接。",
        )
