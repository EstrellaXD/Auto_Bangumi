import re

from bs4 import BeautifulSoup, Tag
from module.network.request_contents import RequestContent
from module.models.bangumi import Episode, DenseInfo

from module.parser.analyser.raw_parser import raw_parser

torrent_url_base = "https://v2.uploadbt.com/?r=down&hash="
pattern = r"^(.+?)\((\d+(?:\.\d+)?)\s*([KMG]?B)\)$"
video_formats = ["mp4", "mkv"]
subtitle_formats = ["ass", "srt"]


def process_file_list(tags: list[Tag]) -> (list[str], int):
    processed = []
    episode_num = 0
    for tag in tags:
        for image in tag.find_all("img"):
            del image
        clazz = tag.attrs.get("class")
        if clazz and "folder" in clazz:
            continue
        match_objs = re.match(pattern, tag.getText())
        if match_objs:
            filename, size, unit = list(map(lambda x: x.strip(), match_objs.groups()))
            if any(filename.lower().endswith(f".{file_format}") for file_format in video_formats):
                if raw_parser(raw=filename, loose=False): # ensure we can parse the episode
                    episode_num = episode_num + 1
                    processed.append(filename)
            if any(filename.lower().endswith(f".{file_format}") for file_format in subtitle_formats):
                    processed.append(filename)
    return processed, episode_num


def kisssub_parser(homepage: str) -> DenseInfo:
    with RequestContent() as req:
        content = req.get_html(homepage)
        soup = BeautifulSoup(content, "html.parser")
        torrent_files = soup.find("div", {"class": "torrent_files"})
        li_tags: list[Tag] = torrent_files.find_all("li")
        file_list, episode_num = process_file_list(li_tags)
        *_, last_element = soup.find("div", {"class": "torrent_files"}).children
        title_web = last_element.getText()
        torrent_hash = soup.find("title").getText()[-40:]
        torrent_url = torrent_url_base + torrent_hash
        return DenseInfo(file_list=file_list, episodes=episode_num, homepage=homepage, title_web=title_web, torrent_url=torrent_url)