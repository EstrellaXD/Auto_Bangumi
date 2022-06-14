import time

from network.request import RequestURL


class GetRssInfo:
    def __init__(self):
        self._req = RequestURL()

    # Mikanani RSS
    def get_titles(self, url):
        soup = self._req.get_content(url)
        items = soup.find_all("item")
        time.sleep(1)
        return [item.title.string for item in items]

    def get_title(self, url):
        soup = self._req.get_content(url)
        item = soup.find("item")
        time.sleep(1)
        return item.title

    def get_torrents(self, url):
        soup = self._req.get_content(url)
        enclosure = soup.find_all("enclosure")
        time.sleep(1)
        return [t["url"] for t in enclosure]


if __name__ == "__main__":
    rss = GetRssInfo()
    try:
        rss.get_title("https://adsasd.com")
    except Exception as e:
        print("connect failed")