"""Domain result returned by the release-title tokenizer.

The tokenizer deliberately keeps missing values as ``None``.  Defaults such as
season 1 and episode 0 belong to the legacy adapter, not to the parser itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MediaType(StrEnum):
    """Kind of media represented by a release."""

    UNKNOWN = "unknown"
    EPISODE = "episode"
    MOVIE = "movie"
    OVA = "ova"
    OAD = "oad"
    SPECIAL = "special"
    PV = "pv"
    OPENING = "opening"
    ENDING = "ending"


class ReleaseKind(StrEnum):
    """Cardinality of a release, independent from its media type."""

    SINGLE = "single"
    RANGE = "range"
    BATCH = "batch"
    COLLECTION = "collection"


@dataclass(frozen=True, slots=True)
class ParsedRelease:
    """Structured, loss-aware representation of a resource name."""

    raw: str
    title_en: str | None = None
    title_zh: str | None = None
    title_jp: str | None = None
    group: str | None = None
    season: int | None = None
    season_raw: str | None = None
    episode: int | float | None = None
    episode_end: int | float | None = None
    episode_title: str | None = None
    media_type: MediaType = MediaType.UNKNOWN
    release_kind: ReleaseKind = ReleaseKind.SINGLE
    resolution: str | None = None
    source: str | None = None
    subtitle: str | None = None
    codecs: tuple[str, ...] = ()
    audio: tuple[str, ...] = ()
    container: str | None = None
    version: int | None = None
    year: int | None = None
    tags: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()

    @property
    def primary_title(self) -> str | None:
        """Return the best available title without applying locale policy."""
        return self.title_en or self.title_zh or self.title_jp

    @property
    def is_movie(self) -> bool:
        return self.media_type is MediaType.MOVIE
