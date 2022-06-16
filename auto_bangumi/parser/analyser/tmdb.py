import re
import time

from network import RequestContent
from conf import settings


class TMDBInfo:
    id: int
    title_jp: str
    title_zh: str
    season: dict
    last_season: int


class TMDBMatcher:
    def __init__(self):
        self.search_url = lambda e: \
            f"https://api.themoviedb.org/3/search/tv?api_key={settings.tdmb_api}&page=1&query={e}&include_adult=false"
        self.info_url = lambda e: \
            f"https://api.themoviedb.org/3/tv/{e}?api_key={settings.tdmb_api}&language=zh-CN"
        self._request = RequestContent()

    def is_animation(self, id):
        url_info = self.info_url(id)
        type_id = self._request.get_json(url_info)["genres"]
        for type in type_id:
            if type["id"] == 16:
                return True
        return False

    # def get_zh_title(self, id):
    #     alt_title_url = self.alt_title_url(id)
    #     titles = self._request.get_content(alt_title_url, content="json")
    #     for title in titles:
    #         if title["iso_3166_1"] == "CN":
    #             return title["title"]
    #     return None

    def get_season(self, seasons: list):
        for season in seasons:
            if re.search(r"第 \d 季", season["season"]) is not None:
                date = season["air_date"].split("-")
                [year, _ , _] = date
                now_year = time.localtime().tm_year
                if int(year) == now_year:
                    return int(re.findall(r"\d", season["season"])[0])

    def tmdb_search(self, title):
        tmdb_info = TMDBInfo()
        url = self.search_url(title)
        contents = self._request.get_json(url)["results"]
        if contents.__len__() == 0:
            url = self.search_url(title.replace(" ", ""))
            contents = self._request.get_json(url)["results"]
        # 判断动画
        for content in contents:
            id = content["id"]
            if self.is_animation(id):
                tmdb_info.id = id
                break
        url_info = self.info_url(tmdb_info.id)
        info_content = self._request.get_json(url_info)
        # 关闭链接
        self._request.close_session()
        tmdb_info.season = [{"season": s["name"], "air_date": s["air_date"]} for s in info_content["seasons"]]
        tmdb_info.last_season = self.get_season(tmdb_info.season)
        tmdb_info.title_jp = info_content["original_name"]
        tmdb_info.title_zh = info_content["name"]
        return tmdb_info


if __name__ == "__main__":
    test = " Love Live！虹咲学园 学园偶像同好会"
    print(TMDBMatcher().tmdb_search(test).title_zh)
