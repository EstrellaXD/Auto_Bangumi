from bs4 import BeautifulSoup
from urllib3.util import parse_url

from module.parser import LocalMikan, MikanParser, RawParser, RemoteMikan


class MikanSearch:
    def __init__(self, url: str, page: RemoteMikan | LocalMikan):
        self.page = page
        self.homepage = url
        self.root_path = parse_url(self.homepage).host
        self.mikan_parser = MikanParser(page=self.page)

    async def search(self):
        content = await self.page.get_content(self.homepage)

        bangumi = await self.mikan_parser.parser(self.homepage)
        poster_link = bangumi.poster_link
        # print(official_title, poster_link)
        soup = BeautifulSoup(content, "html.parser")
        # title bangumi-title
        title = soup.select_one("p.bangumi-title")
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
                bangumi.official_title = title.text
                bangumi.group_name = g.text
                bangumi.rss_link = f"https://{self.root_path}{r.get('href')}"
                bangumi_list.append(bangumi)
                bangumi.poster_link = poster_link
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
            parser = MikanSearch(url=url, page=RemoteMikan())
            result = await parser.search()
        p.print()
        return result

    # code you want to profile
    result = asyncio.run(test())
    for r in result:
        print(r)
