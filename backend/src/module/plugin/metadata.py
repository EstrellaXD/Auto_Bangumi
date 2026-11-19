import re
import time
from collections import OrderedDict
from urllib.parse import urlencode

from ab_sdk.metadata import EpisodeMetadata, MediaDetails, MediaReference

_cache: OrderedDict[str, tuple[float, dict]] = OrderedDict()


def reference(raw, media_type):
    return MediaReference(
        int(raw["id"]),
        media_type,
        raw.get("name") or raw.get("title", ""),
        raw.get("original_name") or raw.get("original_title", ""),
        (raw.get("first_air_date") or raw.get("release_date") or "")[:4] or None,
    )


async def fetch_metadata(path, language, **params):
    from module.network import RequestContent
    from module.parser.analyser.tmdb_parser import _api_key, _tmdb_url

    if not re.fullmatch(r"[a-z]{2}(?:-[A-Z]{2})?", language):
        raise ValueError("Invalid metadata language")
    url = (
        _tmdb_url()
        + "/3/"
        + path
        + "?"
        + urlencode({"api_key": _api_key(), "language": language, **params})
    )
    cached = _cache.get(url)
    if cached and cached[0] > time.monotonic():
        _cache.move_to_end(url)
        return cached[1]
    try:
        async with RequestContent() as request:
            raw = await request.get_json(url)
    except Exception:
        raise RuntimeError("TMDB request failed") from None
    if not isinstance(raw, dict):
        raise RuntimeError("TMDB request failed")
    _cache[url] = time.monotonic() + 3600, raw
    if len(_cache) > 512:
        _cache.popitem(last=False)
    return raw


class HostMetadataService:
    async def search(self, query, *, media_type="tv", language="zh-CN"):
        if media_type not in {"tv", "movie"} or not query.strip():
            raise ValueError("A title and tv/movie type are required")
        raw = await fetch_metadata(
            f"search/{media_type}", language, query=query, include_adult="false"
        )
        return tuple(reference(row, media_type) for row in raw.get("results", []))

    async def get(self, media_id, *, media_type="tv", language="zh-CN"):
        if (
            media_type not in {"tv", "movie"}
            or not isinstance(media_id, int)
            or media_id <= 0
        ):
            raise ValueError("Invalid metadata identity")
        raw = await fetch_metadata(f"{media_type}/{media_id}", language)
        return MediaDetails(
            reference(raw, media_type),
            tuple(
                (int(row["season_number"]), int(row["episode_count"]))
                for row in raw.get("seasons", [])
            ),
            raw.get("status", ""),
        )

    async def episodes(self, tv_id, season, *, language="zh-CN"):
        if (
            not isinstance(tv_id, int)
            or tv_id <= 0
            or not isinstance(season, int)
            or season < 0
        ):
            raise ValueError("Invalid metadata season")
        raw = await fetch_metadata(f"tv/{tv_id}/season/{season}", language)
        return tuple(
            EpisodeMetadata(
                season,
                int(row["episode_number"]),
                row.get("name", ""),
                row.get("air_date"),
            )
            for row in raw.get("episodes", [])
        )
