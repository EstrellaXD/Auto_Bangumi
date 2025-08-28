import logging
import re

from module.conf import settings
from module.database import engine
from module.models import Bangumi, RSSItem, Torrent
from module.parser import MikanParser, RawParser, TmdbParser

logger = logging.getLogger(__name__)


class RSSAnalyser:
    def __init__(
        self,
        _engine=engine,
    ) -> None:
        self.engine = _engine
        self.tmdb_parser: TmdbParser = TmdbParser()
        self.mikan_parser: MikanParser = MikanParser()

    async def official_title_parser(self, bangumi: Bangumi, parser: str, torrent: Torrent) -> Bangumi:
        if parser == "mikan":
            # TODO: MikanParser 要是没有homepage, 降级为 TmdbParser
            try:
                parsered_bangumi = await self.mikan_parser.parser(torrent.homepage)
                if not parsered_bangumi:
                    logger.debug("[Parser] Mikan torrent has no homepage info.")
                    return bangumi
                bangumi.poster_link = parsered_bangumi.poster_link
                bangumi.official_title = parsered_bangumi.official_title
                bangumi.mikan_id = parsered_bangumi.mikan_id
            except AttributeError:
                logger.warning("[Parser] Mikan torrent has no homepage info.")
        else:
            parsered_bangumi = await self.tmdb_parser.parser(
                bangumi.official_title, bangumi.season, settings.rss_parser.language
            )
            if not parsered_bangumi:
                return bangumi
            # FIXME: 如果解析出来的属性是默认值，则不更新
            bangumi.official_title = parsered_bangumi.official_title
            bangumi.year = parsered_bangumi.year
            bangumi.season = parsered_bangumi.season
            bangumi.poster_link = parsered_bangumi.poster_link
            bangumi.tmdb_id = parsered_bangumi.tmdb_id
        bangumi.official_title = re.sub(r"[/:.\\]", " ", bangumi.official_title)
        return bangumi

    async def torrent_to_bangumi(self, torrent: Torrent, rss: RSSItem) -> Bangumi | None:
        """
        parse torrent name to bangumi
        filter 在 RawParser 中设置
        如果只有 rawparser, 则返回 None
        """

        if (bangumi := RawParser().parser(raw=torrent.name)) and bangumi.official_title != "official_title":
            if not await self.official_title_parser(bangumi=bangumi, parser=rss.parser, torrent=torrent):
                logger.debug(f"[RSS analyser] Fail to parse official title for {torrent.name}.")
                return None
            # 这里是最早加入 bangumi.rss_link, bangumi.parser 的地方
            bangumi.rss_link = rss.url
            bangumi.parser = rss.parser
            logger.debug(f"[RSS analyser] Parsed bangumi: {bangumi.official_title} from torrent {torrent.name}")
            return bangumi

    def filer_torrent(self, torrent: Torrent, bangumi: Bangumi) -> bool:
        """
        filter torrent by bangumi
        """
        exclude_filter = bangumi.exclude_filter.replace(",", "|") if bangumi.exclude_filter else ""
        include_filter = bangumi.include_filter.replace(",", "|") if bangumi.include_filter else ""
        if exclude_filter and re.search(exclude_filter, torrent.name):
            logger.debug(
                f"[RSS Filter] Exclude torrent {torrent.name} for {bangumi.official_title},regex: {exclude_filter}"
            )
            return False

        # Check include filter first (if set, torrent must match)
        if include_filter and not re.search(include_filter, torrent.name):
            logger.debug(f"[RSS Filter] Include filter not matched for {torrent.name}, regex: {include_filter}")
            return False
        logger.debug(
            f"[RSS Filter] Torrent {torrent.name} passed filters for {bangumi.official_title}. include_filter: {include_filter}, exclude_filter: {exclude_filter}"
        )
        return True
