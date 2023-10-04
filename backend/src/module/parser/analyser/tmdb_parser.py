import re
import time
from dataclasses import dataclass

from module.conf import TMDB_API
from module.network import RequestContent
from module.utils import save_image

TMDB_URL = "https://api.themoviedb.org"


@dataclass
class TMDBInfo:
    id: int
    title: str
    original_title: str
    season: list[dict]
    last_season: int
    year: str
    poster_link: str = None


LANGUAGE = {"zh": "zh-CN", "jp": "ja-JP", "en": "en-US"}


def search_url(e):
    return f"{TMDB_URL}/3/search/tv?api_key={TMDB_API}&page=1&query={e}&include_adult=false"


def info_url(e, key):
    return f"{TMDB_URL}/3/tv/{e}?api_key={TMDB_API}&language={LANGUAGE[key]}"


def is_animation(tv_id, language) -> bool:
    url_info = info_url(tv_id, language)
    with RequestContent() as req:
        type_id = req.get_json(url_info)["genres"]
        for type in type_id:
            if type.get("id") == 16:
                return True
    return False


def get_season(seasons: list) -> tuple[int, str]:
    ss = [s for s in seasons if s["air_date"] is not None and "特别" not in s["season"]]
    ss = sorted(ss, key=lambda e: e.get("air_date"), reverse=True)
    for season in ss:
        if re.search(r"第 \d 季", season.get("season")) is not None:
            date = season.get("air_date").split("-")
            [year, _, _] = date
            now_year = time.localtime().tm_year
            if int(year) <= now_year:
                return int(re.findall(r"\d", season.get("season"))[0]), season.get(
                    "poster_path"
                )
    return len(ss), ss[-1].get("poster_path")


def tmdb_parser(title, language) -> TMDBInfo | None:
    with RequestContent() as req:
        url = search_url(title)
        contents = req.get_json(url).get("results")
        if contents.__len__() == 0:
            url = search_url(title.replace(" ", ""))
            contents = req.get_json(url).get("results")
        # 判断动画
        if contents:
            for content in contents:
                id = content["id"]
                if is_animation(id, language):
                    break
            url_info = info_url(id, language)
            info_content = req.get_json(url_info)
            season = [
                {
                    "season": s.get("name"),
                    "air_date": s.get("air_date"),
                    "poster_path": s.get("poster_path"),
                }
                for s in info_content.get("seasons")
            ]
            last_season, poster_path = get_season(season)
            if poster_path is None:
                poster_path = info_content.get("poster_path")
            original_title = info_content.get("original_name")
            official_title = info_content.get("name")
            year_number = info_content.get("first_air_date").split("-")[0]
            if poster_path:
                img = req.get_content(f"https://image.tmdb.org/t/p/w780{poster_path}")
                poster_link = save_image(img, "jpg")
            else:
                poster_link = None
            return TMDBInfo(
                id,
                official_title,
                original_title,
                season,
                last_season,
                str(year_number),
                poster_link,
            )
        else:
            return None


if __name__ == "__main__":
    print(tmdb_parser("魔法禁书目录", "zh"))
