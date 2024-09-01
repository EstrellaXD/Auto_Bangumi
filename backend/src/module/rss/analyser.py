import logging
import re

from module.conf import settings
from module.database import engine
from module.models import Bangumi, RSSItem, Torrent
from module.parser import MikanParser, TmdbParser

logger = logging.getLogger(__name__)


class RSSAnalyser:
    def __init__(self, _engine=engine) -> None:
        self.engine = _engine

    @staticmethod
    async def official_title_parser(
        bangumi: Bangumi, rss: RSSItem, torrent: Torrent
    ):
        if rss.parser == "mikan":
            try:
                parsered_bangumi = await MikanParser().parser(torrent.homepage)
                bangumi.poster_link, bangumi.official_title = (
                    parsered_bangumi.poster_link,
                    parsered_bangumi.official_title,
                )
            except AttributeError:
                logger.warning("[Parser] Mikan torrent has no homepage info.")
                pass
        elif rss.parser == "tmdb":
            parsered_bangumi = await TmdbParser.parser(
                bangumi.official_title, bangumi.season, settings.rss_parser.language
            )
            bangumi.official_title = parsered_bangumi.official_title
            bangumi.year = parsered_bangumi.year
            bangumi.season = parsered_bangumi.season
            bangumi.poster_link = parsered_bangumi.poster_link
        else:
            pass
        bangumi.official_title = re.sub(r"[/:.\\]", " ", bangumi.official_title)
