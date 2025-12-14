from models.config import RSSParser

from .mikan_parser import MikanParser
from .parser_config import get_parser_config, set_parser_config
from .title_parser import RawParser
from .torrent_parser import torrent_parser
from .tmdb import tmdb_parser

__all__ = [
    "torrent_parser",
    "RawParser",
    "MikanParser",
    "get_parser_config",
    "tmdb_parser",
]


def init(config: RSSParser | None = None):
    if config is None:
        from conf.config import get_config_by_key

        config = get_config_by_key("rss_parser", RSSParser)
        print("Loaded parser config from conf:", config)
    set_parser_config(config)



