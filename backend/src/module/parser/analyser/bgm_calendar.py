import logging

from module.conf import settings
from module.network import RequestContent

logger = logging.getLogger(__name__)


async def fetch_bgm_calendar() -> list[dict]:
    """Fetch the current season's broadcast calendar from Bangumi.tv API.

    Returns a flat list of anime items with their air_weekday (0=Mon, ..., 6=Sun).
    The base URL is configurable so users behind a GFW can use a mirror (#1040).
    """
    calendar_url = f"{settings.network.bgm_base_url.rstrip('/')}/calendar"
    async with RequestContent() as req:
        data = await req.get_json(calendar_url)

    if not data:
        logger.warning("Failed to fetch calendar data.")
        return []

    items = []
    for day_group in data:
        weekday_info = day_group.get("weekday", {})
        # Bangumi.tv uses 1=Mon, 2=Tue, ..., 7=Sun
        # Convert to 0=Mon, 1=Tue, ..., 6=Sun
        bgm_weekday = weekday_info.get("id")
        if bgm_weekday is None:
            continue
        weekday = bgm_weekday - 1  # 1-7 → 0-6

        for item in day_group.get("items", []):
            items.append(
                {
                    "name": item.get("name", ""),  # Japanese title
                    "name_cn": item.get("name_cn", ""),  # Chinese title
                    "air_weekday": weekday,
                }
            )

    logger.info(f"Fetched {len(items)} airing anime from Bangumi.tv.")
    return items


def match_weekday(
    official_title: str, title_raw: str, calendar_items: list[dict]
) -> int | None:
    """Match a bangumi against calendar items to find its air weekday.

    Matching strategy:
    1. Exact match on Chinese title (name_cn == official_title)
    2. Exact match on Japanese title (name == title_raw or official_title)
    3. Substring match (name_cn in official_title or vice versa)
    4. Substring match on Japanese title
    """
    official_title_clean = official_title.strip()
    title_raw_clean = title_raw.strip()

    for item in calendar_items:
        name_cn = item["name_cn"].strip()
        name = item["name"].strip()

        if not name_cn and not name:
            continue

        # Exact match on Chinese title
        if name_cn and name_cn == official_title_clean:
            return item["air_weekday"]

        # Exact match on Japanese/original title
        if name and (name == title_raw_clean or name == official_title_clean):
            return item["air_weekday"]

    # Second pass: substring matching
    for item in calendar_items:
        name_cn = item["name_cn"].strip()
        name = item["name"].strip()

        if not name_cn and not name:
            continue

        # Chinese title substring (at least 4 chars to avoid false positives)
        if name_cn and len(name_cn) >= 4:
            if name_cn in official_title_clean or official_title_clean in name_cn:
                return item["air_weekday"]

        # Japanese title substring
        if name and len(name) >= 4:
            if name in title_raw_clean or title_raw_clean in name:
                return item["air_weekday"]

    return None
