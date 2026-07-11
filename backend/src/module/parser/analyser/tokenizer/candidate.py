"""Immutable evidence and candidate models used by the title resolver.

Regex rules should only describe what they observed.  They must not mutate the
parse result or remove text from the title.  Semantic candidates group one or
more observations into an interpretation that can be resolved deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .result import MediaType, ReleaseKind


class ClaimField(StrEnum):
    """Scalar and repeatable fields a candidate can contribute."""

    GROUP = "group"
    SEASON = "season"
    SEASON_RAW = "season_raw"
    EPISODE = "episode"
    EPISODE_END = "episode_end"
    EPISODE_TITLE = "episode_title"
    MEDIA_TYPE = "media_type"
    RELEASE_KIND = "release_kind"
    RESOLUTION = "resolution"
    SOURCE = "source"
    SUBTITLE = "subtitle"
    CODECS = "codecs"
    AUDIO = "audio"
    CONTAINER = "container"
    VERSION = "version"
    YEAR = "year"
    TAGS = "tags"


class ShadowedSpanPolicy(StrEnum):
    """Whether valid-but-shadowed metadata remains excluded from the title."""

    EXCLUDE = "exclude"
    KEEP = "keep"


class OverlapPolicy(StrEnum):
    """Whether a candidate may share source characters with another winner."""

    EXCLUSIVE = "exclusive"
    SHARED = "shared"


class DecisionStatus(StrEnum):
    """Outcome of resolving one semantic candidate."""

    SELECTED = "selected"
    SHADOWED = "shadowed"
    REJECTED_AS_TITLE = "rejected_as_title"
    REJECTED_CONFLICT = "rejected_conflict"


@dataclass(frozen=True, slots=True, order=True)
class Span:
    """Half-open character range using coordinates local to one segment."""

    segment: int
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.segment < 0:
            raise ValueError("segment must be non-negative")
        if self.start < 0:
            raise ValueError("span start must be non-negative")
        if self.end <= self.start:
            raise ValueError("span end must be greater than start")

    @property
    def length(self) -> int:
        return self.end - self.start

    def overlaps(self, other: Span) -> bool:
        return (
            self.segment == other.segment
            and self.start < other.end
            and other.start < self.end
        )

    def contains(self, other: Span) -> bool:
        return (
            self.segment == other.segment
            and self.start <= other.start
            and self.end >= other.end
        )


@dataclass(frozen=True, slots=True)
class Observation:
    """A direct, interpretation-free match produced by a tokenizer rule."""

    id: str
    rule_id: str
    kind: str
    span: Span
    text: str
    captures: tuple[str | None, ...] = ()

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("observation id must not be empty")
        if not self.rule_id:
            raise ValueError("observation rule_id must not be empty")
        if not self.kind:
            raise ValueError("observation kind must not be empty")

    @property
    def sort_key(self) -> tuple[int, int, int, str, str]:
        return (
            self.span.segment,
            self.span.start,
            self.span.end,
            self.rule_id,
            self.id,
        )


@dataclass(frozen=True, slots=True)
class Claims:
    """Typed semantic fields proposed by a candidate.

    ``None`` means that the candidate makes no claim for a scalar field.  Empty
    tuples likewise mean no contribution to repeatable fields.
    """

    group: str | None = None
    season: int | None = None
    season_raw: str | None = None
    episode: int | float | None = None
    episode_end: int | float | None = None
    episode_title: str | None = None
    media_type: MediaType | None = None
    release_kind: ReleaseKind | None = None
    resolution: str | None = None
    source: str | None = None
    subtitle: str | None = None
    codecs: tuple[str, ...] = ()
    audio: tuple[str, ...] = ()
    container: str | None = None
    version: int | None = None
    year: int | None = None
    tags: tuple[str, ...] = ()

    def scalar_items(self) -> tuple[tuple[ClaimField, object], ...]:
        values: tuple[tuple[ClaimField, object | None], ...] = (
            (ClaimField.GROUP, self.group),
            (ClaimField.SEASON, self.season),
            (ClaimField.SEASON_RAW, self.season_raw),
            (ClaimField.EPISODE, self.episode),
            (ClaimField.EPISODE_END, self.episode_end),
            (ClaimField.EPISODE_TITLE, self.episode_title),
            (ClaimField.MEDIA_TYPE, self.media_type),
            (ClaimField.RELEASE_KIND, self.release_kind),
            (ClaimField.RESOLUTION, self.resolution),
            (ClaimField.SOURCE, self.source),
            (ClaimField.SUBTITLE, self.subtitle),
            (ClaimField.CONTAINER, self.container),
            (ClaimField.VERSION, self.version),
            (ClaimField.YEAR, self.year),
        )
        return tuple((field, value) for field, value in values if value is not None)

    def repeatable_items(self) -> tuple[tuple[ClaimField, tuple[str, ...]], ...]:
        return (
            (ClaimField.CODECS, self.codecs),
            (ClaimField.AUDIO, self.audio),
            (ClaimField.TAGS, self.tags),
        )

    @property
    def is_empty(self) -> bool:
        return not self.scalar_items() and not any(
            values for _, values in self.repeatable_items()
        )


@dataclass(frozen=True, slots=True)
class Candidate:
    """One semantic interpretation offered to the resolver.

    ``conflict_tags`` and ``blocks`` express cross-field incompatibilities.  A
    strong movie marker, for example, can block the ``ambiguous_episode`` tag
    carried by a trailing bare number without blocking an explicit SxxExx.
    """

    id: str
    rule_id: str
    spans: tuple[Span, ...]
    claims: Claims = Claims()
    priority: int = 0
    specificity: int = 0
    observation_ids: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    conflict_tags: frozenset[str] = frozenset()
    blocks: frozenset[str] = frozenset()
    preserve_as_title_on_conflict: bool = False
    shadowed_span_policy: ShadowedSpanPolicy = ShadowedSpanPolicy.EXCLUDE
    shadowed_spans: tuple[Span, ...] | None = None
    overlap_policy: OverlapPolicy = OverlapPolicy.EXCLUSIVE

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("candidate id must not be empty")
        if not self.rule_id:
            raise ValueError("candidate rule_id must not be empty")
        canonical_spans = tuple(sorted(set(self.spans)))
        object.__setattr__(self, "spans", canonical_spans)
        if self.shadowed_spans is not None:
            canonical_shadowed = tuple(sorted(set(self.shadowed_spans)))
            if not set(canonical_shadowed).issubset(canonical_spans):
                raise ValueError("shadowed_spans must be a subset of spans")
            object.__setattr__(self, "shadowed_spans", canonical_shadowed)

    @property
    def sort_key(self) -> tuple[int, int, tuple[Span, ...], str, str]:
        """Stable ordering key; it never depends on collection insertion order."""
        return (-self.priority, -self.specificity, self.spans, self.rule_id, self.id)


@dataclass(frozen=True, slots=True)
class Decision:
    """Auditable outcome for one candidate."""

    candidate_id: str
    status: DecisionStatus
    reason: str
    won_fields: tuple[ClaimField, ...] = ()
    excluded_spans: tuple[Span, ...] = ()

    @property
    def exclude_from_title(self) -> bool:
        return bool(self.excluded_spans)
