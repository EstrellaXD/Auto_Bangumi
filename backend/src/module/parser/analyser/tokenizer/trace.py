"""Immutable diagnostics for explaining release-title parser decisions."""

from __future__ import annotations

from dataclasses import dataclass

from .candidate import Candidate, Claims, Decision, DecisionStatus, Observation, Span
from .resolver import Resolution, ResolutionWarning
from .result import ParsedRelease


@dataclass(frozen=True, slots=True)
class TraceSegment:
    """Segment snapshot with explicit normalized-text coordinates."""

    index: int
    text: str
    outer_start: int
    outer_end: int
    content_start: int
    content_end: int
    enclosure: str | None = None

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("segment index must be non-negative")
        if not (0 <= self.outer_start <= self.content_start):
            raise ValueError("invalid segment start coordinates")
        if not (self.content_start <= self.content_end <= self.outer_end):
            raise ValueError("invalid segment end coordinates")


@dataclass(frozen=True, slots=True)
class ParseTrace:
    """All observations and resolver decisions for one parser invocation."""

    raw: str
    normalized: str
    segments: tuple[TraceSegment, ...] = ()
    observations: tuple[Observation, ...] = ()
    candidates: tuple[Candidate, ...] = ()
    claims: Claims = Claims()
    decisions: tuple[Decision, ...] = ()
    excluded_spans: tuple[Span, ...] = ()
    residuals: tuple[str, ...] = ()
    warnings: tuple[ResolutionWarning, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "segments", tuple(sorted(self.segments, key=lambda item: item.index))
        )
        object.__setattr__(
            self,
            "observations",
            tuple(sorted(self.observations, key=lambda item: item.sort_key)),
        )
        object.__setattr__(
            self,
            "candidates",
            tuple(sorted(self.candidates, key=lambda item: item.sort_key)),
        )

    @classmethod
    def from_resolution(
        cls,
        *,
        raw: str,
        normalized: str,
        resolution: Resolution,
        segments: tuple[TraceSegment, ...] = (),
        observations: tuple[Observation, ...] = (),
        candidates: tuple[Candidate, ...] = (),
        residuals: tuple[str, ...] = (),
    ) -> ParseTrace:
        return cls(
            raw=raw,
            normalized=normalized,
            segments=segments,
            observations=observations,
            candidates=candidates,
            claims=resolution.claims,
            decisions=resolution.decisions,
            excluded_spans=resolution.excluded_spans,
            residuals=residuals,
            warnings=resolution.warnings,
        )

    def decision_for(self, candidate_id: str) -> Decision:
        for decision in self.decisions:
            if decision.candidate_id == candidate_id:
                return decision
        raise KeyError(candidate_id)

    @property
    def rejected_as_title(self) -> tuple[str, ...]:
        return tuple(
            decision.candidate_id
            for decision in self.decisions
            if decision.status is DecisionStatus.REJECTED_AS_TITLE
        )


@dataclass(frozen=True, slots=True)
class ParseOutcome:
    """Optional parse result paired with its complete diagnostic trace."""

    result: ParsedRelease | None
    trace: ParseTrace
