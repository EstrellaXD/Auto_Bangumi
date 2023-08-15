import re

from module.utils import json_config
from module.models import RSSItem


SEARCH_CONFIG = json_config.load("config/search_provider.json")


def search_url(site: str, keywords: list[str]) -> RSSItem:
    keyword = "+".join(keywords)
    search_str = re.sub(r"[\W_ ]", "+", keyword)
    if site in SEARCH_CONFIG.keys():
        url = re.sub(r"%s", search_str, SEARCH_CONFIG[site].get("url"))
        rss_item = RSSItem(
            url=url,
            parser="mikan"
        )
        return rss_item
    else:
        raise ValueError(f"Site {site} is not supported")