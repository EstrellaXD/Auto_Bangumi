"""Build qBittorrent RSS auto-download rule definitions from a Bangumi entry."""

from module.models import Bangumi, BangumiUpdate


def build_rss_rule(data: Bangumi | BangumiUpdate, save_path: str) -> dict:
    """Construct the qB ``rss/setRule`` payload for one bangumi entry.

    ``rss_link`` is normalised to a comma-joined string when a list slips in
    from the update API. ``save_path`` is passed explicitly because the two
    call sites source it differently (the freshly generated path vs. the moved
    location).
    """
    affected_feeds = (
        data.rss_link if isinstance(data.rss_link, str) else ",".join(data.rss_link)
    )
    return {
        "enable": True,
        "mustContain": data.title_raw,
        "mustNotContain": "|".join(data.filter),
        "useRegex": True,
        "episodeFilter": "",
        "smartFilter": False,
        "previouslyMatchedEpisodes": [],
        "affectedFeeds": affected_feeds,
        "ignoreDays": 0,
        "lastMatch": "",
        "addPaused": False,
        "assignedCategory": "Bangumi",
        "savePath": save_path,
    }
