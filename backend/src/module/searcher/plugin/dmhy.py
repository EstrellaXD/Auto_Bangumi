import re


def dmhy_url(keywords: list[str]):
    keyword = "+".join(keywords)
    search_str = re.sub(r"[\W_ ]", "+", keyword)
    url = f"http://dmhy.org/topics/rss/rss.xml?keyword={search_str}"
    return url
