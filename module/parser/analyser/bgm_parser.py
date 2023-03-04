from module.network import RequestContent


class BgmAPI:
    def __init__(self):
        self.search_url = lambda e: \
            f"https://api.bgm.tv/search/subject/{e}?type=2"
        self.info_url = lambda e: \
            f"https://api.bgm.tv/subject/{e}"
        self._request = RequestContent()

    def search(self, title):
        url = self.search_url(title)
        contents = self._request.get_json(url)["list"]
        if contents.__len__() == 0:
            return None
        return contents[0]["name"], contents[0]["name_cn"]