import re
from dataclasses import dataclass

from network.request import RequestURL
from conf import settings


@dataclass
class TorrentInfo:
    name: str
    torrent_link: str


class RequestContent:
    def __init__(self):
        self._req = RequestURL()

    # Mikanani RSS
    def get_torrents(self, url: str) -> [TorrentInfo]:
        soup = self._req.get_content(url)
        torrent_titles = [item.title.string for item in soup.find_all("item")]
        keep_index = []
        for idx, title in enumerate(torrent_titles):
            if re.search(settings.not_contain, title) is None:
                keep_index.append(idx)
        torrent_urls = [item.get("url") for item in soup.find_all("enclosure")]
        return [TorrentInfo(torrent_titles[i], torrent_urls[i]) for i in keep_index]

    def get_torrent(self, url) -> TorrentInfo:
        soup = self._req.get_content(url)
        item = soup.find("item")
        enclosure = item.find("enclosure")
        return TorrentInfo(item.title.string, enclosure["url"])

    # API JSON
    def get_json(self, url) -> dict:
        return self._req.get_content(url, content="json")

    def close_session(self):
        self._req.close()


if __name__ == "__main__":
    r = RequestContent()
    rss_url = "https://mikanani.me/RSS/Bangumi?bangumiId=2739&subgroupid=203"
    titles = r.get_torrents(rss_url)
    print(settings.not_contain)
    for title in titles:
        print(title.name, title.torrent_link)
