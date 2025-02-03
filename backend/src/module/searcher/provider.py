import re

from module.conf import SEARCH_CONFIG
from module.models import RSSItem


def search_url(site: str, keywords: list[str]) -> RSSItem:
    keyword = "+".join(keywords)
    search_str = re.sub(r"[\W_ ]", "+", keyword)
    if site not in SEARCH_CONFIG.keys():
        raise ValueError(f"Site {site} is not supported")
    url = re.sub(r"%s", search_str, SEARCH_CONFIG[site])
    parser = "mikan" if site == "mikan" else "tmdb"
    return RSSItem(
        url=url,
        aggregate=False,
        parser=parser,
    )
