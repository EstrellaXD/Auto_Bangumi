import logging
import re

from bs4 import BeautifulSoup
from urllib3.util import parse_url

from module.models import MikanInfo
from module.network import RequestContent
from module.utils import gen_poster_path

from . import patterns
from .meta_parser import TitleMetaParser

logger = logging.getLogger("mikan_parser")


class MikanWebParser:
    # 对 mikan 的网页进行解析

    async def parser(self, url) -> MikanInfo:
        async with RequestContent() as req:
            content = await req.get_html(url)
        # logger.debug(f"[MikanWebParser] Parsing URL: {url}")

        mikan_info = MikanInfo()
        if not content:
            logger.debug(f"[MikanWebParser] No content found for {url}")
            return mikan_info
        soup = BeautifulSoup(content, "html.parser")
        # logger.debug("[MikanWebParser] Content fetched successfully")
        official_title = soup.select_one('p.bangumi-title')
        # logger.debug(f"[MikanWebParser] Official title found: {official_title}")
        if official_title:
            # official_title: <a class="w-other-c" href="/Home/Bangumi/3391#583" style="color:#555" target="_blank">败犬女主太多了！</a>
            # mikan_id = re.search(r".*/Home/Bangumi/(\d+(#\d+)?)", str(official_title))
            # https://mikanani.me/RSS/Bangumi?bangumiId=3060&subgroupid=583
            # mikan_id = re.search(r"Bangumi?bangumiId=(\d+)(&subgroupid=(\d+))?,
            rss = soup.select_one('a[href^="/RSS/Bangumi?bangumiId="]')
                                 # (#\d+)?", str(official_title))
            if not rss:
                logger.debug(f"[MikanWebParser] No RSS link found for {url}")
                return mikan_info
            rss_url = rss.get("href")
            if not rss_url:
                logger.debug(f"[MikanWebParser] No RSS URL found for {url}")
                return mikan_info

            mikan_id = ""
            if isinstance(rss_url, str):
                bangumi_id = re.search(r"bangumiId=(\d+)", rss_url)
                subgroup_id = re.search(r"subgroupid=(\d+)", rss_url)
                if bangumi_id:
                    mikan_id = bangumi_id.group(1)
                    if subgroup_id:
                        mikan_id += "#" + subgroup_id.group(1)



            official_title = official_title.text
            eps_info = TitleMetaParser().parser(official_title)
            title = re.sub(patterns.SEASON_RE, "", official_title + " ")
            title = title.strip()
            logger.debug(
                f"[MikanWebParser] Parsed title: {title}, mikan_id: {mikan_id}"
            )
            mikan_info.id = mikan_id
            mikan_info.official_title = title
            mikan_info.season = eps_info.season
            mikan_info.poster_link = await self.poster_parser(url)
            logger.debug(f"[MikanWebParser] Parsed mikan info: {mikan_info}")
        return mikan_info

    async def poster_parser(self, url) -> str:
        poster_link = ""
        # content = await self.page.get_content(self.homepage)
        async with RequestContent() as req:
            content = await req.get_html(url)
        root_path = parse_url(url).host
        if not content:
            return ""
        soup = BeautifulSoup(content, "html.parser")
        poster_div = soup.find("div", {"class": "bangumi-poster"}).get("style")
        if poster_div:
            poster_path = poster_div.split("url('")[1].split("')")[0]
            poster_link = f"https://{root_path}{poster_path}"
            poster_link = gen_poster_path(poster_link)
        return poster_link

    async def bangumi_link_parser(self, url) -> str:
        async with RequestContent() as req:
            content = await req.get_html(url)
        if not content:
            return ""
        root_path = parse_url(url).host
        soup = BeautifulSoup(content, "html.parser")
        bangumi_link = soup.select_one('p.bangumi-title a[href^="/Home/Bangumi/"]')
        if bangumi_link:
            bangumi_link = f"https://{root_path}{bangumi_link.get('href')}"
            # https://mikanani.me/Home/Bangumi/3391#583
            bangumi_link = re.sub(r"#.*", "", bangumi_link)
        else:
            bangumi_link = ""
        return bangumi_link


if __name__ == "__main__":
    import asyncio
    import time

    url = "https://mikanani.me/RSS/Bangumi?bangumiId=3661&subgroupid=370"
    url = "https://mikanani.me/Home/Bangumi/3391"
    # url = "https://mikanani.me/Home/Episode/d69f77ab14a1b7aa6eec778d84e979e0d6e9916e"
    # page = BaseWebPage(url)
    parser = MikanWebParser()
    start = time.time()
    result = asyncio.run(parser.parser(url))
    print(result)
    end = time.time()
    print(f"Time taken: {end - start} seconds")
    start = time.time()

    result = asyncio.run(parser.bangumi_link_parser(url))
    end = time.time()
    print(f"Time taken: {end - start} seconds")

    start = time.time()
    result = asyncio.run(parser.parser(url))
    end = time.time()
    print(f"Time taken: {end - start} seconds")
    print(result)
