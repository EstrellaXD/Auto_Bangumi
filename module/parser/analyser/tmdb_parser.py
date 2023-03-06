import re
import time
from dataclasses import dataclass

from module.network import RequestContent
from module.conf import TMDB_API


@dataclass
class TMDBInfo:
    id: int
    title_jp: str
    title_zh: str
    season: dict
    last_season: int
    year_number: int


class TMDBMatcher:
    def __init__(self):
        self.search_url = lambda e: \
            f"https://api.themoviedb.org/3/search/tv?api_key={TMDB_API}&page=1&query={e}&include_adult=false"
        self.info_url = lambda e: \
            f"https://api.themoviedb.org/3/tv/{e}?api_key={TMDB_API}&language=zh-CN"
        self._request = RequestContent()

    def is_animation(self, tv_id) -> bool:
        url_info = self.info_url(tv_id)
        type_id = self._request.get_json(url_info)["genres"]
        for type in type_id:
            if type.get("id") == 16:
                return True
        return False

    # def get_zh_title(self, id):
    #     alt_title_url = self.alt_title_url(id)
    #     titles = self._request.get_content(alt_title_url, content="json")
    #     for title in titles:
    #         if title["iso_3166_1"] == "CN":
    #             return title["title"]
    #     return None

    @staticmethod
    def get_season(seasons: list) -> int:
        for season in seasons:
            if re.search(r"第 \d 季", season.get("season")) is not None:
                date = season.get("air_date").split("-")
                [year, _ , _] = date
                now_year = time.localtime().tm_year
                if int(year) == now_year:
                    return int(re.findall(r"\d", season.get("season"))[0])

    def tmdb_search(self, title) -> TMDBInfo:
        url = self.search_url(title)
        contents = self._request.get_json(url).get("results")
        if contents.__len__() == 0:
            url = self.search_url(title.replace(" ", ""))
            contents = self._request.get_json(url).get("results")
        # 判断动画
        for content in contents:
            id = content["id"]
            if self.is_animation(id):
                break
        url_info = self.info_url(id)
        info_content = self._request.get_json(url_info)
        # 关闭链接
        self._request.close()
        season = [{"season": s.get("name"), "air_date": s.get("air_date")} for s in info_content.get("seasons")]
        last_season = self.get_season(season)
        title_jp = info_content.get("original_name")
        title_zh = info_content.get("name")
        year_number = info_content.get("first_air_date").split("-")[0]
        return TMDBInfo(id, title_jp, title_zh, season, last_season, year_number)