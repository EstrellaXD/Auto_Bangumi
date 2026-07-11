"""Business admission policies for generic parsed releases.

Parsing answers what a resource name contains.  These helpers answer whether a
particular consumer can safely use that result.  Keeping the policy outside the
tokenizer prevents download/database constraints from leaking into parsing.
"""

from __future__ import annotations

from enum import StrEnum

from module.parser.analyser.tokenizer.result import (
    MediaType,
    ParsedRelease,
    ReleaseKind,
)


class PersistenceTarget(StrEnum):
    BANGUMI = "bangumi"
    MOVIE = "movie"


_SPECIAL_MEDIA = {MediaType.OVA, MediaType.OAD, MediaType.SPECIAL}
_NUMBERED_MEDIA = {MediaType.EPISODE, *_SPECIAL_MEDIA}
_NON_PERSISTED_MEDIA = {MediaType.PV, MediaType.OPENING, MediaType.ENDING}


def has_release_evidence(release: ParsedRelease) -> bool:
    """Whether a title-only result still looks like an actual release name."""
    return bool(
        release.group
        or release.resolution
        or release.source
        or release.subtitle
        or release.codecs
        or release.audio
        or release.container
    )


def is_weak_title_only(release: ParsedRelease) -> bool:
    """Whether parsing found only a title, with no release-shaped evidence."""
    return bool(
        release.primary_title
        and release.media_type is MediaType.UNKNOWN
        and release.release_kind is ReleaseKind.SINGLE
        and release.episode is None
        and not has_release_evidence(release)
    )


def persistence_target(release: ParsedRelease) -> PersistenceTarget | None:
    """Return the database projection currently supported for a release."""
    if (
        not release.primary_title
        or release.release_kind is not ReleaseKind.SINGLE
        or release.media_type in _NON_PERSISTED_MEDIA
    ):
        return None
    if release.media_type is MediaType.MOVIE:
        return PersistenceTarget.MOVIE
    if is_weak_title_only(release):
        return None
    return PersistenceTarget.BANGUMI


def bangumi_episode_type(release: ParsedRelease) -> str:
    return "special" if release.media_type in _SPECIAL_MEDIA else "episode"


def normalized_season(release: ParsedRelease, *, default: int = 1) -> int:
    if release.media_type in _SPECIAL_MEDIA:
        return 0
    return release.season if release.season is not None else default


def preference_identity(
    release: ParsedRelease, *, default_season: int = 1
) -> tuple[MediaType, int, int | float] | None:
    """Return a safe identity for release-preference deduplication."""
    if (
        release.release_kind is not ReleaseKind.SINGLE
        or release.media_type not in _NUMBERED_MEDIA
        or release.episode is None
    ):
        return None
    return (
        release.media_type,
        normalized_season(release, default=default_season),
        release.episode,
    )


def preference_revision(release: ParsedRelease) -> int:
    """Rank revisions of the same content; an unmarked release is revision 1."""
    return release.version if release.version is not None else 1


def is_offset_signal(release: ParsedRelease) -> bool:
    """Whether a release is a safe weekly-episode signal for offset detection."""
    return bool(
        release.media_type is MediaType.EPISODE
        and release.release_kind is ReleaseKind.SINGLE
        and type(release.episode) is int
        and release.episode > 0
    )
