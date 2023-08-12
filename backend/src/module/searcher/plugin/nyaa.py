import re


def nyaa_url(keywords: list[str]):
    keyword = "+".join(keywords)
    search_str = re.sub(r"[\W_ ]", "+", keyword)
    url = f"https://nyaa.si/?page=rss&q={search_str}&c=0_0&f=0"
    return url
