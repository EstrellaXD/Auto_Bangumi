import time
from dataclasses import dataclass

from module.parser.api.tmdb import (
    TMDB_IMG_URL,
    ShowInfo,
    TMDBInfoAPI,
    TMDBSearchAPI,
    TVShow,
)
from module.utils import gen_poster_path


@dataclass
class TMDBInfo:
    id: int
    title: str
    original_title: str
    season: int
    last_season: int
    year: str
    poster_link: str = ""


async def is_animation(genre_ids: list[int]) -> bool:
    # grnres_id 内有, 不用再请求一次
    #
    if 16 in genre_ids:
        return True
    return False


def get_season(seasons: list[dict[str, str]]) -> tuple[int, str]:
    # sort by season number
    ss = [s for s in seasons if s["air_date"] is not None and s["season"]]
    ss = sorted(ss, key=lambda e: e.get("air_date"), reverse=True)
    for season in ss:
        date = season.get("air_date").split("-")
        [year, _, _] = date
        now_year = time.localtime().tm_year
        if int(year) <= now_year:
            return int(season.get("season")), season.get("poster_path")
    return len(ss), ss[-1].get("poster_path")


async def find_animation(contents: list[ShowInfo]) -> ShowInfo | None:
    # 类似狼与香辛料, 会存在多个结果,但动画前面的就覆盖了
    sorted_contents = sorted(
        contents, key=lambda e: e.get("first_air_date"), reverse=True
    )
    for content in sorted_contents:
        genre_ids: list[int] = content["genre_ids"]
        if await is_animation(genre_ids):
            return content
    return None


async def tmdb_parser(
    title: str,
    language: str,
    search_api: TMDBSearchAPI = TMDBSearchAPI(),
    info_api: TMDBInfoAPI = TMDBInfoAPI(),
) -> TMDBInfo | None:
    contents = await search_api.get_content(title)
    if not contents:
        contents = await search_api.get_content(title.replace(" ", ""))
    if not contents:
        return None
    # # 判断动画
    content = await find_animation(contents)
    if content := await find_animation(contents):
        url_info = await info_api.get_content(content["id"], language)
        info_content: TVShow = url_info
        season = [
            {
                "season": s.get("season_number"),
                "air_date": s.get("air_date"),
                "poster_path": s.get("poster_path"),
            }
            for s in info_content.get("seasons")
        ]
        last_season, poster_path = get_season(season)
        original_title: str = info_content.get("original_name")
        official_title: str = info_content.get("name")
        year_number = info_content.get("first_air_date").split("-")[0]
        id = info_content.get("id")
        poster_link = ""
        if poster_path:
            poster_link = f"{TMDB_IMG_URL}{poster_path}"
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

    ans = asyncio.run(tmdb_parser("Re：从零开始的异世界生活 袭击篇", "zh"))
    # ans = asyncio.run(tmdb_parser("物语系列", "zh"))
    print(ans)
