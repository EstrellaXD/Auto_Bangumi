import re

from module.conf import SEARCH_CONFIG
from module.models import RSSItem


def search_url(site: str, keywords: list[str]) -> RSSItem:
    keyword = "+".join(keywords)
    search_str = re.sub(r"[\W_ ]", "+", keyword)
    if site in SEARCH_CONFIG.keys():
        url = re.sub(r"%s", search_str, SEARCH_CONFIG[site])
        parser = parser if site in ["mikan", "kisssub"] else "tmdb"
        rss_item = RSSItem(
            url=url,
            aggregate=False,
            parser=parser,
        )
        return rss_item
    else:
        raise ValueError(f"Site {site} is not supported")
