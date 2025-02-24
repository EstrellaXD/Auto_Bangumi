import re

from bs4 import BeautifulSoup
from urllib3.util import parse_url

from module.parser.api.baseapi import BaseWebPage
from module.utils import gen_poster_path

# TODO:改进official_title 作为标识, tmdb有id, mikan也有bangumi id


class MikanWebParser:
    # 对 mikan 的网页进行解析

    def __init__(self, url: str, page: BaseWebPage):
        self.page = page
        self.homepage = url
        self.root_path = parse_url(self.homepage).host

    async def parser(self):
        content = await self.page.get_content(self.homepage)
        soup = BeautifulSoup(content, "html.parser")
        official_title = soup.select_one('p.bangumi-title a[href^="/Home/Bangumi/"]')
        if official_title:
            official_title = official_title.text
            official_title = re.sub(r"第.*季", "", official_title).strip()
        else:
            official_title = ""
        return official_title

    async def poster_parser(self):
        poster_link = ""
        content = await self.page.get_content(self.homepage)
        soup = BeautifulSoup(content, "html.parser")
        poster_div = soup.find("div", {"class": "bangumi-poster"}).get("style")
        if poster_div:
            poster_path = poster_div.split("url('")[1].split("')")[0]
            poster_link = f"https://{self.root_path}{poster_path}"
            poster_link = gen_poster_path(poster_link)
        return poster_link

    async def bangumi_link_parser(self):
        content = await self.page.get_content(self.homepage)
        soup = BeautifulSoup(content, "html.parser")
        bangumi_link = soup.select_one('p.bangumi-title a[href^="/Home/Bangumi/"]')
        if bangumi_link:
            bangumi_link = f"https://{self.root_path}{bangumi_link.get('href')}"
            # https://mikanani.me/Home/Bangumi/3391#583
            bangumi_link = re.sub(r"#.*", "", bangumi_link)
        else:
            bangumi_link = ""
        return bangumi_link


if __name__ == "__main__":
    import asyncio
    import time

    url = "https://mikanani.me/Home/Episode/b42bf9c357beffe9ed24a36a39190983b7dec40a"
    page = BaseWebPage(url)
    parser = MikanWebParser(url, page)
    start = time.time()
    result = asyncio.run(parser.bangumi_link_parser())
    end = time.time()
    print(f"Time taken: {end - start} seconds")
    start = time.time()
    result = asyncio.run(parser.parser())
    end = time.time()
    print(f"Time taken: {end - start} seconds")
    print(result)
