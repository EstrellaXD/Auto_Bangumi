import logging
import re

from bs4 import BeautifulSoup
from urllib3.util import parse_url

from module.network import RequestContent
from module.utils import save_image

logger = logging.getLogger(__name__)

# In-memory cache for Mikan homepage lookups
_mikan_cache: dict[str, tuple[str, str]] = {}


async def mikan_parser(homepage: str):
    if homepage in _mikan_cache:
        return _mikan_cache[homepage]
    root_path = parse_url(homepage).host
    if not root_path:
        logger.warning("[Mikan] Invalid homepage URL: %s", homepage)
        return ("", "")
    async with RequestContent() as req:
        content = await req.get_html(homepage)
        if not content:
            logger.warning("[Mikan] Failed to fetch homepage: %s", homepage)
            return ("", "")
        soup = BeautifulSoup(content, "html.parser")

        poster_link = ""
        poster_div = soup.find("div", {"class": "bangumi-poster"})
        if poster_div is None:
            logger.warning("[Mikan] No poster div found on: %s", homepage)
        else:
            poster_style = poster_div.get("style")
            if poster_style and "url('" in poster_style:
                try:
                    poster_path = poster_style.split("url('")[1].split("')")[0]
                    poster_path = poster_path.split("?")[0]
                    img = await req.get_content(f"https://{root_path}{poster_path}")
                    if img:
                        suffix = poster_path.rsplit(".", 1)[-1] if "." in poster_path else "jpg"
                        poster_link = save_image(img, suffix)
                    else:
                        logger.warning("[Mikan] Failed to download poster from: %s", homepage)
                except (IndexError, ValueError) as e:
                    logger.warning("[Mikan] Failed to parse poster style on %s: %s", homepage, e)
            else:
                logger.warning("[Mikan] Poster div has no style or url() on: %s", homepage)

        official_title = ""
        title_elem = soup.select_one('p.bangumi-title a[href^="/Home/Bangumi/"]')
        if title_elem is None:
            logger.warning("[Mikan] No official title found on: %s", homepage)
        else:
            official_title = re.sub(r"第.*季", "", title_elem.text).strip()

        # 只缓存成功结果（失败不缓存，下次 rss_loop 会重试）
        if poster_link and official_title:
            _mikan_cache[homepage] = (poster_link, official_title)
        return (poster_link, official_title)


if __name__ == '__main__':
    import asyncio
    homepage = "https://mikanani.me/Home/Episode/c89b3c6f0c1c0567a618f5288b853823c87a9862"
    print(asyncio.run(mikan_parser(homepage)))
