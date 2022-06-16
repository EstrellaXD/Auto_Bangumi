from network.request import RequestURL


class RequestContent:
    def __init__(self):
        self._req = RequestURL()

    # Mikanani RSS
    def get_titles(self, url):
        soup = self._req.get_content(url)
        items = soup.find_all("item")
        return [item.title.string for item in items]

    def get_title(self, url):
        soup = self._req.get_content(url)
        item = soup.find("item")
        return item.title.string

    def get_torrents(self, url):
        soup = self._req.get_content(url)
        enclosure = soup.find_all("enclosure")
        return [t["url"] for t in enclosure]

    # API JSON
    def get_json(self, url):
        return self._req.get_content(url, content="json")

    def close_session(self):
        self._req.close()


if __name__ == "__main__":
    r = RequestContent()
    url = "https://mikanani.me/RSS/Bangumi?bangumiId=2685&subgroupid=552"
    title = r.get_title(url)
    print(title)