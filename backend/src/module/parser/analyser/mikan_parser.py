import re

from bs4 import BeautifulSoup
from urllib3.util import parse_url

from module.network import RequestContent
from module.utils import save_image


async def mikan_parser(homepage: str):
    root_path = parse_url(homepage).host
    async with RequestContent() as req:
        content = await req.get_html(homepage)
        soup = BeautifulSoup(content, "html.parser")
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
            poster_link = save_image(img, suffix)
            return poster_link, official_title
        return "", ""


if __name__ == '__main__':
    import asyncio
    homepage = "https://mikanani.me/Home/Episode/c89b3c6f0c1c0567a618f5288b853823c87a9862"
    print(asyncio.run(mikan_parser(homepage)))
