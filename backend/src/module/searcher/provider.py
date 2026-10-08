import re

from ab_sdk import points
from ab_sdk.search import SearchSite
from module.conf.search_provider import ProviderConfig, get_provider
from module.models import RSSItem
from module.plugin.host import get_registry


def available_sites() -> dict[str, ProviderConfig]:
    """可用搜索站点：插件提供的站点 + 用户配置的站点（同名时用户配置优先）。

    每次调用都重新读取，用户保存的站点与插件启停都能立即生效。
    """
    sites: dict[str, ProviderConfig] = {}
    for site_id, entry in get_registry().providers(points.SEARCH_SITE).items():
        site: SearchSite = entry.factory()
        sites[site_id] = {"url": site.url, "parser": site.parser}
    sites.update(get_provider())
    return sites


def search_url(site: str, keywords: list[str]) -> RSSItem:
    keyword = "+".join(keywords)
    search_str = re.sub(r"[\W_ ]", "+", keyword)
    providers = available_sites()
    if site in providers:
        # str.replace, not re.sub: the template is a literal "%s" placeholder,
        # and search_str may itself contain regex-special characters.
        url = providers[site]["url"].replace("%s", search_str)
        parser = providers[site]["parser"]
        rss_item = RSSItem(
            url=url,
            aggregate=False,
            parser=parser,
        )
        return rss_item
    else:
        raise ValueError(f"Site {site} is not supported")
