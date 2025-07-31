import logging
import re

from module.conf import settings
from module.database import Database, engine
from module.models import Bangumi, RSSItem, Torrent
from module.parser import MikanParser, RawParser, TmdbParser
from module.utils import gen_save_path

logger = logging.getLogger(__name__)


class RSSAnalyser:
    def __init__(
        self,
        _engine=engine,
        tmdb_parser: TmdbParser = TmdbParser(),
        mikan_parser: MikanParser = MikanParser(),
    ) -> None:
        self.engine = _engine
        self.tmdb_parser = tmdb_parser
        self.mikan_parser = mikan_parser

    async def official_title_parser(
        self, bangumi: Bangumi, parser: str, torrent: Torrent
    ) -> Bangumi:
        if parser == "mikan":
            # TODO: MikanParser 要是没有homepage, 降级为 TmdbParser
            try:
                parsered_bangumi = await self.mikan_parser.parser(torrent.homepage)
                if not parsered_bangumi:
                    logger.debug("[Parser] Mikan torrent has no homepage info.")
                    return bangumi
                bangumi.poster_link = parsered_bangumi.poster_link
                bangumi.official_title = parsered_bangumi.official_title
            except AttributeError:
                logger.warning("[Parser] Mikan torrent has no homepage info.")
        # else rss.parser == "tmdb":
        else:
            parsered_bangumi = await self.tmdb_parser.parser(
                bangumi.official_title, bangumi.season, settings.rss_parser.language
            )
            if not parsered_bangumi:
                return bangumi
            # if parsered_bangumi porperty is not default value, update bangumi
            # FIXME: 如果解析出来的属性是默认值，则不更新
            bangumi.official_title = parsered_bangumi.official_title
            bangumi.year = parsered_bangumi.year
            bangumi.season = parsered_bangumi.season
            bangumi.poster_link = parsered_bangumi.poster_link
        bangumi.official_title = re.sub(r"[/:.\\]", " ", bangumi.official_title)
        return bangumi

    async def torrent_to_bangumi(self, torrent: Torrent, rss: RSSItem) -> Bangumi | None:
        """
        parse torrent name to bangumi
        filter 在 RawParser 中设置
        如果只有 rawparser, 则返回 None
        """

        with Database(engine) as database:
            bangumi = database.find_bangumi_by_torrent(torrent,rss.aggregate)
            if bangumi:
                logger.debug(f"[RSS analyser] Find bangumi {bangumi.official_title} by torrent {torrent.name}")
                return bangumi
        if (
            bangumi :=RawParser().parser(raw=torrent.name)
        ) and bangumi.official_title != "official_title":
            if not await self.official_title_parser(
                bangumi=bangumi, parser=rss.parser, torrent=torrent
            ):
                logger.debug(
                    f"[RSS analyser] Fail to parse official title for {torrent.name}."
                )
                return None
            bangumi.rss_link = rss.url
            bangumi.parser = rss.parser
            logger.debug(f"[RSS analyser] Parsed bangumi: {bangumi.official_title} from torrent {torrent.name}")
            return bangumi



if __name__ == "__main__":
    import asyncio
    import time

    async def test():
        analyser = RSSAnalyser()
        start = time.time()
        res = await analyser.torrent_to_bangumi(test_torrent, rss_item)
        end = time.time()
        start = time.time()
        res = await analyser.torrent_to_bangumi(test_torrent, rss_item)
        end = time.time()
        return res

    test_bangumi = Bangumi(official_title="败犬女主太多了！", season=1)
    test_torrent = Torrent(
        name="败犬女主太多了！ S01E01",
        homepage="https://mikanani.me/Home/Episode/33fbab8f53fe4bad12f07afa5abdb7c4afa5956c",
    )
    rss_item = RSSItem(url="https://mikanani.me/RSS/Bangumi/100000", parser="mikan")

    res = asyncio.run(test())
