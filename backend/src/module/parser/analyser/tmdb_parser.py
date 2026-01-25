import logging
import re
import time
from dataclasses import dataclass

from module.conf import TMDB_API
from module.network import RequestContent
from module.utils import save_image

logger = logging.getLogger(__name__)

TMDB_URL = "https://api.themoviedb.org"

# In-memory cache for TMDB lookups to avoid repeated API calls
_tmdb_cache: dict[str, "TMDBInfo | None"] = {}


@dataclass
class TMDBInfo:
    id: int
    title: str
    original_title: str
    season: list[dict]
    last_season: int
    year: str
    poster_link: str = None
    series_status: str = None  # "Ended", "Returning Series", etc.
    season_episode_counts: dict[int, int] = None  # {1: 13, 2: 12, ...}

    def get_offset_for_season(self, season: int) -> int:
        """Calculate offset for a season (negative sum of all previous seasons' episodes).

        Used when RSS episode numbers are absolute (e.g., S02E18 should be S02E05).
        Returns the offset to subtract from the parsed episode number.
        """
        if not self.season_episode_counts or season <= 1:
            return 0
        return -sum(self.season_episode_counts.get(s, 0) for s in range(1, season))


LANGUAGE = {"zh": "zh-CN", "jp": "ja-JP", "en": "en-US"}


def search_url(e):
    return f"{TMDB_URL}/3/search/tv?api_key={TMDB_API}&page=1&query={e}&include_adult=false"


def info_url(e, key):
    return f"{TMDB_URL}/3/tv/{e}?api_key={TMDB_API}&language={LANGUAGE[key]}"


async def is_animation(tv_id, language, req: RequestContent) -> bool:
    url_info = info_url(tv_id, language)
    type_id = await req.get_json(url_info)
    if type_id:
        for type in type_id.get("genres", []):
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


async def tmdb_parser(title, language, test: bool = False) -> TMDBInfo | None:
    cache_key = f"{title}:{language}"
    if cache_key in _tmdb_cache:
        logger.debug(f"[TMDB] Cache hit for {title}")
        return _tmdb_cache[cache_key]

    async with RequestContent() as req:
        url = search_url(title)
        contents = await req.get_json(url)
        if not contents:
            return None
        contents = contents.get("results")
        if contents.__len__() == 0:
            url = search_url(title.replace(" ", ""))
            contents_resp = await req.get_json(url)
            if not contents_resp:
                return None
            contents = contents_resp.get("results")
        # 判断动画
        if contents:
            for content in contents:
                id = content["id"]
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
            # Extract series status (e.g., "Ended", "Returning Series")
            series_status = info_content.get("status")
            # Extract episode counts per season (exclude specials at season 0)
            season_episode_counts = {
                s.get("season_number"): s.get("episode_count", 0)
                for s in info_content.get("seasons", [])
                if s.get("season_number", 0) > 0
            }
            if poster_path is None:
                poster_path = info_content.get("poster_path")
            original_title = info_content.get("original_name")
            official_title = info_content.get("name")
            year_number = info_content.get("first_air_date").split("-")[0]
            if poster_path:
                if not test:
                    img = await req.get_content(f"https://image.tmdb.org/t/p/w780{poster_path}")
                    poster_link = save_image(img, "jpg")
                else:
                    poster_link = "https://image.tmdb.org/t/p/w780" + poster_path
            else:
                poster_link = None
            result = TMDBInfo(
                id=id,
                title=official_title,
                original_title=original_title,
                season=season,
                last_season=last_season,
                year=str(year_number),
                poster_link=poster_link,
                series_status=series_status,
                season_episode_counts=season_episode_counts,
            )
            _tmdb_cache[cache_key] = result
            return result
        else:
            _tmdb_cache[cache_key] = None
            return None


if __name__ == "__main__":
    import asyncio
    print(asyncio.run(tmdb_parser("魔法禁书目录", "zh")))
