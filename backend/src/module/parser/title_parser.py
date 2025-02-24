import asyncio
import logging
from abc import abstractmethod

from module.conf import settings
from module.models import Bangumi
from module.models.bangumi import Episode
from module.parser.analyser import MikanWebParser, tmdb_parser, torrent_parser
from module.parser.analyser import RawParser as rawparser
from module.parser.api import BaseWebPage, TMDBInfoAPI, TMDBSearchAPI

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


class RawParser:

    @abstractmethod
    def parser(title: str, **kwargs) -> Bangumi:
        pass


class TmdbParser(RawParser):
    def __init__(
        self,
        search_api: TMDBSearchAPI = TMDBSearchAPI(),
        info_api: TMDBInfoAPI = TMDBInfoAPI(),
    ):
        self.search_api = search_api
        self.info_api = info_api

    async def parser(self, title: str, season: int = 1, language: str = "zh"):
        tmdb_info = await tmdb_parser(title, language, self.search_api, self.info_api)
        if tmdb_info:
            logger.debug(
                f"[Title Parser] TMDB Matched, official title is {tmdb_info.title}"
            )
            tmdb_season = tmdb_info.last_season if tmdb_info.last_season else season
            # return tmdb_info.title, tmdb_season, tmdb_info.year, tmdb_info.poster_link
            return Bangumi(
                official_title=tmdb_info.title,
                title_raw=title,
                year=tmdb_info.year,
                season=tmdb_season,
                poster_link=tmdb_info.poster_link,
            )

        else:
            logger.warning(
                f"[Title Parser]Cannot match {title} in TMDB. Use raw title instead."
            )
            logger.warning("[Title Parser]Please change bangumi info manually.")
            return None
            # return Bangumi(
            #     official_title=title,
            #     title_raw=title,
            #     season=season,
            # )

    async def poster_parser(self, bangumi: Bangumi) -> bool:
        tmdb_info = await tmdb_parser(
            bangumi.official_title,
            settings.rss_parser.language,
            self.search_api,
            self.info_api,
        )
        if tmdb_info:
            logger.debug(
                f"[Title Parser] TMDB Matched, official title is {tmdb_info.title}"
            )
            bangumi.poster_link = tmdb_info.poster_link
            return True
        else:
            logger.warning(
                f"[Title Parser] Cannot match {bangumi.official_title} in TMDB. Use raw title instead."
            )
            logger.warning("[Title Parser] Please change bangumi info manually.")
            return False


class MikanParser(RawParser):
    def __init__(self, page: BaseWebPage = BaseWebPage()):
        self.page = page

    async def parser(self, homepage: str) -> Bangumi:
        mikan_parser = MikanWebParser(homepage, self.page)
        tasks = [mikan_parser.parser(), mikan_parser.poster_parser()]
        official_title, poster_link = await asyncio.gather(*tasks)
        if not official_title or not poster_link:
            return None

        return Bangumi(
            official_title=official_title,
            poster_link=poster_link,
        )

    async def poster_parser(self, homepage: str) -> str:
        mikan_parser = MikanWebParser(homepage, self.page)
        poster_link = await mikan_parser.poster_parser()
        if not poster_link:
            return ""
        return poster_link

    async def bangumi_link_parser(self, homepage: str) -> str:
        mikan_parser = MikanWebParser(homepage, self.page)
        return await mikan_parser.bangumi_link_parser()


class RawParser(RawParser):
    @staticmethod
    def parser(raw: str) -> Bangumi | None:
        language = settings.rss_parser.language
        try:
            # use OpenAI ChatGPT to parse raw title and get structured data
            # if settings.experimental_openai.enable:
            #     kwargs = settings.experimental_openai.dict(exclude={"enable"})
            #     gpt = analyser.OpenAIParser(**kwargs)
            #     episode_dict = gpt.parse(raw, asdict=True)
            #     episode = Episode(**episode_dict)
            # else:
            episode: Episode = rawparser().parser(raw)

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
            logger.debug(f"RAW:{raw} >> {title_raw}")
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
                filter=",".join(settings.rss_parser.filter),
            )
        except Exception as e:
            logger.debug(e)
            logger.warning(f"Cannot parse {raw}.")
            return None


class TitleParser:
    def __init__(self):
        pass

    @staticmethod
    def torrent_parser(
        torrent_name: str,
        file_type: str = "media",
    ):
        try:
            return torrent_parser(
                torrent_name,
                file_type,
            )
        except Exception as e:
            logger.warning(f"Cannot parse {torrent_name} with error {e}")


if __name__ == "__main__":
    import asyncio
    import time

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

    # parser = TmdbParser()

    title = "/Volumes/gtx/download/qb/动漫/物语系列/Season 5"
    language = "zh"
    season = 1
    official_title = "败犬女主太多了！"
    homepage = (
        "https://mikanani.me/Home/Episode/33fbab8f53fe4bad12f07afa5abdb7c4afa5956c"
    )

    ans = asyncio.run(test(homepage))
    print(ans)
