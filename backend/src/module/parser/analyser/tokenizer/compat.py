"""Compatibility projection from generic tokenizer results to ``Episode``."""

from __future__ import annotations

from module.models import Episode

from .parser import parse_release_title
from .result import MediaType, ParsedRelease, ReleaseKind

_SPECIAL_MEDIA = {
    MediaType.OVA,
    MediaType.OAD,
    MediaType.SPECIAL,
}


def to_legacy_episode(parsed: ParsedRelease) -> Episode | None:
    """Project a generic result onto the historical parser contract.

    The old API is intentionally conservative: a plain title with neither an
    episode nor a strong resource-kind marker remains unparseable.  New callers
    should use :func:`parse_release_title` to receive such partial results.
    """
    if not parsed.primary_title:
        return None
    if parsed.is_mixed_collection:
        return None
    if parsed.release_kind in {ReleaseKind.RANGE, ReleaseKind.BATCH}:
        return None
    if parsed.media_type in {
        MediaType.PV,
        MediaType.OPENING,
        MediaType.ENDING,
    }:
        return None
    if isinstance(parsed.episode, float):
        return None
    if (
        parsed.episode is None
        and parsed.media_type is MediaType.UNKNOWN
        and parsed.release_kind is not ReleaseKind.COLLECTION
    ):
        return None

    if parsed.media_type is MediaType.MOVIE:
        episode_type = "movie"
        season = parsed.season if parsed.season is not None else 1
    elif parsed.media_type in _SPECIAL_MEDIA:
        episode_type = "special"
        season = 0
    else:
        episode_type = "episode"
        season = parsed.season if parsed.season is not None else 1

    return Episode(
        title_en=parsed.title_en,
        title_zh=parsed.title_zh,
        title_jp=parsed.title_jp,
        season=season,
        season_raw=parsed.season_raw or "",
        episode=parsed.episode if parsed.episode is not None else 0,
        sub=parsed.subtitle,
        group=parsed.group or "",
        resolution=parsed.resolution,
        source=parsed.source,
        episode_type=episode_type,
    )


def legacy_non_episodic_type(media_type: MediaType) -> str | None:
    """Map a generic media type to the legacy non-episodic classifier."""
    if media_type is MediaType.MOVIE:
        return "movie"
    if media_type in _SPECIAL_MEDIA:
        return "special"
    return None


def tokenize_title(raw: str) -> Episode | None:
    """Return the historical ``Episode`` projection used by RSS callers."""
    parsed = parse_release_title(raw)
    return to_legacy_episode(parsed) if parsed is not None else None
