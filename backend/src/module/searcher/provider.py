import re

# SEARCH_CONFIG is re-exported for existing importers (module.searcher.__init__);
# search_url itself reads get_provider() below so provider updates saved via
# save_provider() take effect immediately instead of only after a restart.
from module.conf.search_provider import SEARCH_CONFIG, get_provider  # noqa: F401
from module.models import RSSItem


def search_url(site: str, keywords: list[str]) -> RSSItem:
    keyword = "+".join(keywords)
    search_str = re.sub(r"[\W_ ]", "+", keyword)
    providers = get_provider()
    if site in providers:
        # str.replace, not re.sub: the template is a literal "%s" placeholder,
        # and search_str may itself contain regex-special characters.
        url = providers[site].replace("%s", search_str)
        parser = "mikan" if site == "mikan" else "tmdb"
        rss_item = RSSItem(
            url=url,
            aggregate=False,
            parser=parser,
        )
        return rss_item
    else:
        raise ValueError(f"Site {site} is not supported")
