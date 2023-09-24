from bs4 import BeautifulSoup
from urllib3.util import parse_url

from module.network import RequestContent


def mikan_parser(homepage: str):
    root_path = parse_url(homepage).host
    with RequestContent() as req:
        content = req.get_html(homepage)
        soup = BeautifulSoup(content, "html.parser")
        poster_div = soup.find("div", {"class": "bangumi-poster"})
        poster_style = poster_div.get("style")
        official_title = soup.select_one(
            'p.bangumi-title a[href^="/Home/Bangumi/"]'
        ).text
        if poster_style:
            poster_path = poster_style.split("url('")[1].split("')")[0]
            poster_link = f"https://{root_path}{poster_path}"
            return poster_link, official_title
        return "", ""
