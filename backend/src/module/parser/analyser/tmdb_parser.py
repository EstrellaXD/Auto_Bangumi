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
    virtual_season_starts: dict[int, list[int]] = None  # {1: [1, 29], ...} - episode numbers where virtual seasons start

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


def season_url(tv_id, season_number, key):
    return f"{TMDB_URL}/3/tv/{tv_id}/season/{season_number}?api_key={TMDB_API}&language={LANGUAGE[key]}"


async def is_animation(tv_id, language, req: RequestContent) -> bool:
    url_info = info_url(tv_id, language)
    type_id = await req.get_json(url_info)
    if type_id:
        for type in type_id.get("genres", []):
            if type.get("id") == 16:
                return True
    return False


async def get_season_episode_air_dates(tv_id: int, season_number: int, language: str, req: RequestContent) -> list[dict]:
    """Get episode air dates for a season.

    Returns:
        List of {episode_number, air_date} dicts, sorted by episode number
    """
    import datetime

    url = season_url(tv_id, season_number, language)
    season_data = await req.get_json(url)
    if not season_data:
        return []

    episodes = []
    for ep in season_data.get("episodes", []):
        ep_num = ep.get("episode_number")
        air_date_str = ep.get("air_date")
        if ep_num and air_date_str:
            try:
                air_date = datetime.date.fromisoformat(air_date_str)
                episodes.append({"episode_number": ep_num, "air_date": air_date})
            except ValueError:
                continue

    return sorted(episodes, key=lambda x: x["episode_number"])


def detect_virtual_seasons(episodes: list[dict], gap_months: int = 6) -> list[int]:
    """Detect virtual season breakpoints based on air date gaps.

    When there's a gap > gap_months between consecutive episodes,
    it indicates a "cour break" or "virtual season" boundary.

    Args:
        episodes: List of {episode_number, air_date} dicts
        gap_months: Minimum gap in months to consider a season break (default 6)

    Returns:
        List of episode numbers where virtual seasons START (e.g., [1, 29] means S1 starts at ep1, S2 at ep29)
    """
    import datetime

    if len(episodes) < 2:
        return [1] if episodes else []

    virtual_season_starts = [1]  # First virtual season always starts at episode 1
    gap_days = gap_months * 30  # Approximate months to days

    for i in range(1, len(episodes)):
        prev_ep = episodes[i - 1]
        curr_ep = episodes[i]
        days_diff = (curr_ep["air_date"] - prev_ep["air_date"]).days

        if days_diff > gap_days:
            virtual_season_starts.append(curr_ep["episode_number"])
            logger.debug(
                f"[TMDB] Detected virtual season break: {days_diff} days gap "
                f"between ep{prev_ep['episode_number']} and ep{curr_ep['episode_number']}"
            )

    return virtual_season_starts


async def get_aired_episode_count(tv_id: int, season_number: int, language: str, req: RequestContent) -> int:
    """Get the count of episodes that have actually aired for a season.

    Args:
        tv_id: TMDB TV show ID
        season_number: Season number
        language: Language code
        req: Request content instance

    Returns:
        Number of episodes that have aired (air_date <= today)
    """
    import datetime

    url = season_url(tv_id, season_number, language)
    season_data = await req.get_json(url)
    if not season_data:
        return 0

    episodes = season_data.get("episodes", [])
    today = datetime.date.today()
    aired_count = 0

    for ep in episodes:
        air_date_str = ep.get("air_date")
        if air_date_str:
            try:
                air_date = datetime.date.fromisoformat(air_date_str)
                if air_date <= today:
                    aired_count += 1
            except ValueError:
                # Invalid date format, skip this episode
                continue

    logger.debug(f"[TMDB] Season {season_number}: {aired_count} aired of {len(episodes)} total episodes")
    return aired_count


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
            # For ongoing series, we need to get actual aired episode counts
            season_episode_counts = {}
            virtual_season_starts = {}
            for s in info_content.get("seasons", []):
                season_num = s.get("season_number", 0)
                if season_num > 0:
                    total_eps = s.get("episode_count", 0)
                    # Get episode air dates for virtual season detection
                    episodes = await get_season_episode_air_dates(id, season_num, language, req)
                    if episodes:
                        # Detect virtual seasons based on air date gaps
                        vs_starts = detect_virtual_seasons(episodes)
                        if len(vs_starts) > 1:
                            virtual_season_starts[season_num] = vs_starts
                            logger.debug(f"[TMDB] Season {season_num} has virtual seasons starting at episodes: {vs_starts}")
                        # Count only aired episodes
                        season_episode_counts[season_num] = len(episodes)
                    else:
                        season_episode_counts[season_num] = total_eps
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
                virtual_season_starts=virtual_season_starts if virtual_season_starts else None,
            )
            _tmdb_cache[cache_key] = result
            return result
        else:
            _tmdb_cache[cache_key] = None
            return None


if __name__ == "__main__":
    import asyncio
    print(asyncio.run(tmdb_parser("魔法禁书目录", "zh")))
