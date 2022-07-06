import re
import time

from network import RequestContent
from conf import settings


class BangumiAPI:
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



if __name__ == '__main__':
    BGM = BangumiAPI()
    print(BGM.search("辉夜大小姐"))