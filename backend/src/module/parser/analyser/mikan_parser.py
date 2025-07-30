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

    async def parser(self) -> tuple[str, str]:
        content = await self.page.get_content(self.homepage)
        if not content:
            return "", ""
        soup = BeautifulSoup(content, "html.parser")
        official_title = soup.select_one('p.bangumi-title a[href^="/Home/Bangumi/"]')
        print(f"official_title: {official_title}")
        if official_title:
            # official_title: <a class="w-other-c" href="/Home/Bangumi/3391#583" style="color:#555" target="_blank">败犬女主太多了！</a>
            # mikan_id = re.search(r".*/Home/Bangumi/(\d+(#\d+)?)", str(official_title))
            mikan_id = re.search(r"/Home/Bangumi/(\d+)(#\d+)?", str(official_title))
            if mikan_id:
                mikan_id = mikan_id.group(1) + (mikan_id.group(2) or "")
            else:
                mikan_id = ""
            official_title = official_title.text
            print(f"official_title: {official_title}")
            official_title = re.sub(r"第.*季", "", official_title).strip()
            print(f"mikan_id: {mikan_id}")
        else:
            official_title = ""
        return official_title, mikan_id

    async def poster_parser(self) -> str:
        poster_link = ""
        content = await self.page.get_content(self.homepage)
        if not content:
            return ""
        soup = BeautifulSoup(content, "html.parser")
        poster_div = soup.find("div", {"class": "bangumi-poster"}).get("style")
        if poster_div:
            poster_path = poster_div.split("url('")[1].split("')")[0]
            poster_link = f"https://{self.root_path}{poster_path}"
            poster_link = gen_poster_path(poster_link)
        return poster_link

    async def bangumi_link_parser(self) -> str:
        content = await self.page.get_content(self.homepage)
        if not content:
            return ""
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
