import asyncio
import logging
from abc import abstractmethod

from module.conf import settings
from module.models import Bangumi
from module.models.bangumi import Episode
from module.parser import analyser

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

    @staticmethod
    @abstractmethod
    def parser(title: str, **kwargs) -> Bangumi:
        pass


class TmdbParser(RawParser):

    @staticmethod
    async def parser(title: str, season: int = 1, language: str = "zh"):
        tmdb_info = await analyser.tmdb_parser(title, language)
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

            return Bangumi(
                official_title=title,
                title_raw=title,
                season=season,
            )

    @staticmethod
    async def poster_parser(bangumi: Bangumi):
        tmdb_info = await analyser.tmdb_parser(
            bangumi.official_title, settings.rss_parser.language
        )
        if tmdb_info:
            logger.debug(
                f"[Title Parser] TMDB Matched, official title is {tmdb_info.title}"
            )
            bangumi.poster_link = tmdb_info.poster_link
        else:
            logger.warning(
                f"[Title Parser] Cannot match {bangumi.official_title} in TMDB. Use raw title instead."
            )
            logger.warning("[Title Parser] Please change bangumi info manually.")


class MikanParser(RawParser):
    @staticmethod
    async def parser(homepage: str) -> tuple[str, str]:

        mikan_parser = analyser.MikanParser(homepage)
        tasks = [mikan_parser.parser(), mikan_parser.poster_parser()]
        official_title, poster_link = await asyncio.gather(*tasks)

        return Bangumi(
            official_title=official_title,
            poster_link=poster_link,
        )


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
            episode: Episode = analyser.RawParser().parser(raw)

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
            return analyser.torrent_parser(
                torrent_name,
                file_type,
            )
        except Exception as e:
            logger.warning(f"Cannot parse {torrent_name} with error {e}")


if __name__ == "__main__":
    import asyncio

    async def test(title):
        tb = RawParser().parser(title)
        return RawParser.parser(tb.title_raw)

    # parser = TmdbParser()

    title = "/Volumes/gtx/download/qb/动漫/物语系列/Season 5"
    language = "zh"
    season = 1
    official_title = "败犬女主太多了！"

    ans = asyncio.run(test(title))
    print(ans)
