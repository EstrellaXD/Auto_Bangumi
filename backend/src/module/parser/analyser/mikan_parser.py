import logging
import re
from collections import OrderedDict

from bs4 import BeautifulSoup
from urllib3.util import parse_url

from module.network import RequestContent
from module.utils import save_image

logger = logging.getLogger(__name__)

# In-memory cache for Mikan homepage lookups. Keyed by per-episode homepage
# URL, so it is bounded (LRU-ish, oldest-evicted) rather than unlimited.
_MIKAN_CACHE_MAX = 512
_mikan_cache: "OrderedDict[str, tuple[str, str]]" = OrderedDict()


def reset_cache() -> None:
    """清空 Mikan 主页解析缓存。配置重载后必须调用，否则会继续返回旧配置下
    缓存的结果。"""
    _mikan_cache.clear()


def _cache_result(homepage: str, result: tuple[str, str]) -> tuple[str, str]:
    if len(_mikan_cache) >= _MIKAN_CACHE_MAX:
        _mikan_cache.popitem(last=False)
    _mikan_cache[homepage] = result
    return result


async def mikan_parser(homepage: str):
    if homepage in _mikan_cache:
        return _mikan_cache[homepage]
    root_path = parse_url(homepage).host
    async with RequestContent() as req:
        content = await req.get_html(homepage)
        # get_html returns None on a failed fetch; feed BeautifulSoup an empty
        # string instead of None so a network failure surfaces as a normal
        # "element not found" AttributeError rather than an uncaught TypeError.
        soup = BeautifulSoup(content or "", "html.parser")
        poster_div = soup.find("div", {"class": "bangumi-poster"}).get("style")
        official_title = soup.select_one(
            'p.bangumi-title a[href^="/Home/Bangumi/"]'
        ).text
        official_title = re.sub(r"第.*季", "", official_title).strip()
        if poster_div:
            poster_path = poster_div.split("url('")[1].split("')")[0]
            poster_path = poster_path.split("?")[0]
            img = await req.get_content(f"https://{root_path}{poster_path}")
            suffix = poster_path.split(".")[-1]
            # img can be None if the poster download failed; don't crash on it.
            poster_link = await save_image(img, suffix) if img else ""
            return _cache_result(homepage, (poster_link, official_title))
        return _cache_result(homepage, ("", official_title))


if __name__ == "__main__":
    import asyncio

    homepage = (
        "https://mikanani.me/Home/Episode/c89b3c6f0c1c0567a618f5288b853823c87a9862"
    )
    print(asyncio.run(mikan_parser(homepage)))
