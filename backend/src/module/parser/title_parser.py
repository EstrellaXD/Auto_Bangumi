import asyncio
import logging
from abc import abstractmethod

from typing_extensions import override

from models import (
    Bangumi,
    Episode,
    EpisodeFile,
    SubtitleFile,
)

from .meta_parser import TitleMetaParser
from .parser_config import get_parser_config

# from .tmdb_parser import tmdb_parser

logger = logging.getLogger(__name__)

"""
重命名用到的地方
1. rss 拉取的时候会调用一个 raw parser, 然后检查有没有bangumi,最后是用mikan or tmdb parser
2. 重命名的时候会调用一个 raw parser, 现在也会在之后调用 tmdb parser
目前看起来 都是先用的 raw parser, 然后再用 另外一个 parser
所以 raw_parser 单独出来, 会返回一个 bangumi 
然后再用其他的 parser 来处理这个 bangumi

抽象出来一个 API 类, 主要是对网络请求的封装, 用来处理网络请求, 这样可以test的时候mock
对于 TMDB, 是先用名字去查, 然后再去拿详细信息, tmdb 要用到 title, season, language,id
对于 Mikan, 是要拿到homepage,然后拿到页面, 然后解析
主要的东西是要 official_title, poster_link, season
"""

# parsrt_config = RSSParser()


class BaseParser:
    @abstractmethod
    def parser(self, title: str, **kwargs) -> Bangumi | None:
        pass


# class TmdbParser(BaseParser):
#     def __init__(self):
#         pass
#
#     @override
#     async def parser(self, title: str, season: int = 1, language: str = "zh"):
#         tmdb_info = await tmdb_parser(title, language)
#         if tmdb_info:
#             logger.debug(f"[Title Parser] TMDB Matched, official title is {tmdb_info.title}")
#             tmdb_season = tmdb_info.last_season if tmdb_info.last_season else season
#             # return tmdb_info.title, tmdb_season, tmdb_info.year, tmdb_info.poster_link
#             return Bangumi(
#                 official_title=tmdb_info.title,
#                 title_raw=title,
#                 year=tmdb_info.year,
#                 season=tmdb_season,
#                 poster_link=tmdb_info.poster_link,
#                 tmdb_id=str(tmdb_info.id),
#             )
#
#         else:
#             logger.warning(f"[Title Parser]Cannot match {title} in TMDB. Use raw title instead.")
#             logger.warning("[Title Parser]Please change bangumi info manually.")
#             return None
#
#     async def poster_parser(self, bangumi: Bangumi) -> bool:
#         tmdb_info = await tmdb_parser(
#             bangumi.official_title,
#            parser_config.language,
#         )
#         if tmdb_info:
#             logger.debug(f"[Title Parser] TMDB Matched, official title is {tmdb_info.title}")
#             bangumi.poster_link = tmdb_info.poster_link
#             bangumi.tmdb_id = str(tmdb_info.id)
#             return True
#         else:
#             logger.warning(f"[Title Parser] Cannot match {bangumi.official_title} in TMDB. Use raw title instead.")
#             logger.warning("[Title Parser] Please change bangumi info manually.")
#             return False


# class MikanParser(BaseParser):
#     def __init__(self):
#         pass
#
#     async def parser(self, homepage: str) -> Bangumi | None:
#         mikan_parser = MikanWebParser()
#         mikan_info: MikanInfo = await mikan_parser.parser(homepage)
#         if not mikan_info.official_title or not mikan_info.poster_link or not mikan_info.id:
#             logger.debug(f"[MikanParser] No official title or poster link found for {homepage}")
#             return None
#
#         return Bangumi(
#             official_title=mikan_info.official_title,
#             season=mikan_info.season,
#             mikan_id=mikan_info.id,
#             poster_link=mikan_info.poster_link,
#         )
#
#     async def poster_parser(self, bangumi: Bangumi) -> bool:
#         # 这是给 Bangumi 刷新用的
#         # https://mikanani.me/Home/Bangumi/
#         if not bangumi.mikan_id:
#             logger.debug(f"[MikanParser] No Mikan ID found for {bangumi.official_title}")
#             return False
#         homepage = f"https://{parser_config.mikan_custom_url}/Home/Bangumi/{bangumi.mikan_id}"
#         logger.debug(f"[MikanParser] Parsing poster link from {homepage}")
#         mikan_parser = MikanWebParser()
#         poster_link = await mikan_parser.poster_parser(homepage)
#         if not poster_link:
#             return False
#         bangumi.poster_link = poster_link
#         return True
#
#     async def bangumi_link_parser(self, homepage: str) -> str:
#         mikan_parser = MikanWebParser()
#         return await mikan_parser.bangumi_link_parser(homepage)


class RawParser(BaseParser):
    def parser(self, title: str, exclude_collection: bool = False) -> Bangumi | None:
        config = get_parser_config()
        language = config.language
        # try:
        episode: Episode = TitleMetaParser().parser(title)
        if exclude_collection and episode.episode == -1:
            return None

        titles = {
            "zh": episode.title_zh,
            "en": episode.title_en,
            "jp": episode.title_jp,
        }
        title_raw = episode.title_en if episode.title_en else episode.title_zh
        if titles[language]:
            official_title = titles[language]
        elif titles["zh"]:
            official_title = titles["zh"]
        elif titles["en"]:
            official_title = titles["en"]
        elif titles["jp"]:
            official_title = titles["jp"]
        else:
            official_title = title_raw
        _season = episode.season
        # logger.debug(f"[RawParser] RAW:{raw} >> {title_raw}")
        return Bangumi(
            official_title=official_title,
            title_raw=title_raw,
            year=None,
            season=_season,
            season_raw=episode.season_raw,
            group_name=episode.group,
            dpi=episode.resolution,
            source=episode.source,
            subtitle=episode.sub,
            eps_collect=False if episode.episode > 1 else True,
            offset=0,
            exclude_filter=",".join(config.filter),
            include_filter=",".join(config.include),
        )


# class TitleParser:
#     def __init__(self):
#         pass
#
#     @staticmethod
#     def torrent_parser(
#         torrent_name: str,
#     ) -> EpisodeFile | SubtitleFile | None:
#         try:
#             return torrent_parser(torrent_name)
#         except Exception as e:
#             logger.warning(f"Cannot parse {torrent_name} with error {e}")


if __name__ == "__main__":
    import asyncio
    import time

    mikan_id = "3649#357"
    from module.log import setup_logger

    setup_logger(logging.DEBUG, reset=True)

    mikan_url = get_parser_config().mikan_custom_url
    homepage = f"https://{mikan_url}/Home/Bangumi/{mikan_id}"

    async def test(title):
        start = time.time()
        tb = MikanParser()
        ans = await tb.parser(title)
        end = time.time()
        print(f"Time taken: {end - start} seconds")
        start = time.time()
        ans = await tb.parser(title)
        end = time.time()
        print(f"Time taken: {end - start} seconds")
        return ans

    async def test_mikan_poster(homepage):
        start = time.time()
        tb = MikanParser()
        ans = await tb.poster_parser(homepage)
        end = time.time()
        print(f"Time taken: {end - start} seconds")
        return ans

    # parser = TmdbParser()

    title = "/Volumes/gtx/download/qb/动漫/物语系列/Season 5"
    language = "zh"
    season = 1
    official_title = "败犬女主太多了！"
    # homepage = (
    #     "https://mikanani.me/Home/Episode/33fbab8f53fe4bad12f07afa5abdb7c4afa5956c"
    # )

    ans = asyncio.run(test_mikan_poster(homepage))
    print(ans)
