from datetime import datetime

from models import (
    SearchResult,
    SeasonTMDB,
    ShowInfo,
    TMDBInfo,
    TVShow,
)
from module.network import RequestContent
from module.utils import gen_poster_path

from .parser_config import TMDB_IMG_URL, info_url, search_url


async def tmdb_search(key_word: str) -> list[ShowInfo]:
    """
    按关键词搜索 TMDB 电视节目。
    返回经过验证的 ShowInfo 对象列表。
    """
    url = search_url(key_word)
    async with RequestContent() as req:
        json_contents = await req.get_json(url)
        if json_contents:
            search_result = SearchResult.model_validate(json_contents)
            return search_result.results
        return []


async def tmdb_info(id: str, language: str) -> TVShow | None:
    """
    获取 TMDB 节目详细信息。
    返回经过验证的 TVShow 对象。
    """
    url = info_url(id, language)
    async with RequestContent() as req:
        json_contents = await req.get_json(url)
        if json_contents:
            return TVShow.model_validate(json_contents)
        return None


def is_animation(genre_ids: list[int]) -> bool:
    """判断是否为动画类型（genre_id=16 为动画）"""
    return 16 in genre_ids


def get_latest_season(seasons: list[SeasonTMDB]) -> SeasonTMDB | None:
    """获取最新已播出的季度信息"""
    current_time = datetime.now()
    valid_seasons: list[SeasonTMDB] = []

    for s in seasons:
        if s.air_date and s.season_number > 0:
            try:
                air_date = datetime.strptime(s.air_date, "%Y-%m-%d")
                if air_date < current_time:
                    valid_seasons.append(s)
            except ValueError:
                continue

    if valid_seasons:
        return sorted(valid_seasons, key=lambda e: e.air_date or "", reverse=True)[0]

    # 回退：从原始列表找任意 season_number > 0 的
    for s in seasons:
        if s.season_number > 0:
            return s

    return None


def find_animation(contents: list[ShowInfo]) -> ShowInfo | None:
    """
    从搜索结果中查找动画类型的节目。
    类似狼与香辛料，会存在多个结果，优先返回最新的动画。
    """
    sorted_contents = sorted(
        contents,
        key=lambda e: e.first_air_date or "",
        reverse=True,
    )
    for content in sorted_contents:
        if is_animation(content.genre_ids):
            return content
    return None


async def tmdb_parser(
    title: str,
    language: str,
) -> TMDBInfo | None:
    """
    解析 TMDB 信息，返回 TMDBInfo 对象。
    """
    contents = await tmdb_search(title)
    if not contents:
        contents = await tmdb_search(title.replace(" ", ""))
    if not contents:
        return None

    content = find_animation(contents)
    if not content:
        return None

    info_content = await tmdb_info(str(content.id), language)
    if not info_content:
        return None

    latest_season = get_latest_season(info_content.seasons)
    if not latest_season or not latest_season.poster_path:
        return None

    first_air_date = info_content.first_air_date or ""
    year = first_air_date.split("-")[0] if first_air_date else ""

    poster_link = f"{TMDB_IMG_URL}{latest_season.poster_path}"
    poster_link = gen_poster_path(poster_link)

    return TMDBInfo(
        id=info_content.id,
        title=info_content.name,
        original_title=info_content.original_name,
        year=year,
        air_date=latest_season.air_date or "",
        episode_count=latest_season.episode_count,
        season=latest_season.season_number,
        poster_link=poster_link,
        vote_average=info_content.vote_average,
    )


if __name__ == "__main__":
    import asyncio

    ans = asyncio.run(tmdb_parser("Re：从零开始的异世界生活", "zh"))
    # ans = asyncio.run(tmdb_parser("物语系列", "zh"))
    print(ans)
