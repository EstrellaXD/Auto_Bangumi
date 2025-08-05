import re

from bs4 import BeautifulSoup
from urllib3.util import parse_url

from module.network import RequestContent
from module.parser import RawParser
from module.parser import MikanParser
import logging
logger = logging.getLogger(__name__)


class MikanSearch:
    def __init__(self, url: str):
        self.homepage = url
        self.root_path = parse_url(self.homepage).host

    async def search(self):
        raw_bangumi = await MikanParser().parser(self.homepage)
        if not raw_bangumi:
            logger.debug(
                f"[MikanSearch] No bangumi found for {self.homepage}, maybe the page is not a valid bangumi page."
            )
            return []
        async with RequestContent() as req:
            content = await req.get_html(self.homepage)
        if not content:
            return []

        # TODO: 对poster_link 进行处理
        # https://mikanani.me/images/Bangumi/202407/7572c0f6.jpg?width=400&height=400&format=webp
        # 因为不同的图片大小可能会解析失败, 所以直接去掉 width 和 height
        soup = BeautifulSoup(content, "html.parser")
        # title bangumi-title
        # find group from soup <a href="/Home/PublishGroup/991" target="_blank" style="color: #3bc0c3;">TensoRaws</a>
        # find group from soup <a href="/Home/PublishGroup/991" target="_blank" style="color: #3bc0c3;">TensoRaws</a>
        # a 在subgroup-text 下
        # group = soup.find_all("a", href=re.compile(r"/Home/PublishGroup/\d+"))
        group = soup.select(".subgroup-text a[href^='/Home/PublishGroup/']")
        rsslink = soup.select(".subgroup-text a[href^='/RSS/Bangumi?']")
        tbody = soup.select("tbody")
        bangumi_list = []
        for g, r, t in zip(group, rsslink, tbody):
            bangumi = t.select(".magnet-link-wrap")
            for b in bangumi:
                bangumi = RawParser().parser(b.text)
                bangumi.official_title = raw_bangumi.official_title
                bangumi.group_name = g.text
                bangumi.rss_link = f"https://{self.root_path}{r.get('href')}"
                bangumi_list.append(bangumi)
                bangumi.poster_link = raw_bangumi.poster_link
                break
        return bangumi_list
        # # 从 homepage 提取季度 , 字幕组, rsslink
        # # 从 homepage 提取季度 , 字幕组, rsslink

        # return soup


if __name__ == "__main__":
    import asyncio

    import pyinstrument

    async def test():
        p = pyinstrument.Profiler()
        with p:
            url = "https://mikanani.me/Home/Bangumi/3519"
            parser = MikanSearch(url=url)
            result = await parser.search()
        p.print()
        return result

    # code you want to profile
    result = asyncio.run(test())
    for r in result:
        print(r)
