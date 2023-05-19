import re

from module.conf import settings


def mikan_url(keywords: list[str]):
    keyword = "+".join(keywords)
    search_str = re.sub(r"[\W_ ]", "+", keyword)
    url = f"{settings.rss_parser.custom_url}/RSS/Search?searchstr={search_str}"
    if "://" not in url:
        url = f"https://{url}"
    return url

