import re
import time
from dataclasses import dataclass

from module.conf import TMDB_API
from module.network import RequestContent
from module.utils import save_image,gen_poster_path

TMDB_URL = "https://api.themoviedb.org"


@dataclass
class TMDBInfo:
    id: int
    title: str
    original_title: str
    season: list[dict]
    last_season: int
    year: str
    poster_link: str|None = None


LANGUAGE = {"zh": "zh-CN", "jp": "ja-JP", "en": "en-US"}


def search_url(e):
    return f"{TMDB_URL}/3/search/tv?api_key={TMDB_API}&page=1&query={e}&include_adult=false"


def info_url(e, key):
    return f"{TMDB_URL}/3/tv/{e}?api_key={TMDB_API}&language={LANGUAGE[key]}"


async def is_animation(tv_id:int, language:str, req) -> bool:
    url_info = info_url(tv_id, language)
    type_ids = await req.get_json(url_info)
    for type in type_ids["genres"]:
        if type.get("id") == 16:
            return True
    return False


def get_season(seasons: list[dict[str, str]]) -> tuple[int, str]:
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


async def tmdb_parser(title:str, language:str, test: bool = False) -> TMDBInfo | None:
    async with RequestContent() as req:
        url = search_url(title)
        json_contents = await req.get_json(url)
        contents:list[dict[str,int|float|list[int|float|str]]] = json_contents.get("results", "")
        # TODO: 还是怪怪的
        if contents.__len__() == 0:
            url = search_url(title.replace(" ", ""))
            json_contents = await req.get_json(url)
            contents = json_contents.get("results", "")
        # # 判断动画
        if contents:
            for content in contents:
                id:int = content["id"]
                if await is_animation(id, language, req):
                    break
            url_info = info_url(id, language)
            info_content = await req.get_json(url_info)

            season = [
                {
                    "season": s.get("name"),
                    "air_date": s.get("air_date"),
                    "poster_path": s.get("poster_path"),
                }
                for s in info_content.get("seasons")
            ]
            last_season, poster_path = get_season(season)
            # TODO: 什么情况会是 None?
            if poster_path is None:
                poster_path:str = info_content.get("poster_path")

            original_title:str = info_content.get("original_name")
            official_title:str = info_content.get("name")
            year_number = info_content.get("first_air_date").split("-")[0]
            poster_link = None
            if poster_path:
                poster_link = f"https://image.tmdb.org/t/p/w780{poster_path}"
                poster_link = gen_poster_path(poster_link)

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
    import asyncio

    ans = asyncio.run(tmdb_parser("蓝色监狱 (2022)", "zh"))
    # print(ans)
