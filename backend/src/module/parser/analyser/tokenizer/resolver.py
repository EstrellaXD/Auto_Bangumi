"""Deterministic conflict resolution for tokenizer candidates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from .candidate import (
    Candidate,
    ClaimField,
    Claims,
    Decision,
    DecisionStatus,
    OverlapPolicy,
    ShadowedSpanPolicy,
    Span,
)
from .result import MediaType, ReleaseKind


@dataclass(frozen=True, slots=True)
class Resolution:
    """Resolved semantic values plus the decisions that produced them."""

    claims: Claims
    decisions: tuple[Decision, ...]
    excluded_spans: tuple[Span, ...]
    evidence: tuple[str, ...]
    warnings: tuple[ResolutionWarning, ...] = ()

    @property
    def selected_candidate_ids(self) -> tuple[str, ...]:
        return tuple(
            decision.candidate_id
            for decision in self.decisions
            if decision.status is DecisionStatus.SELECTED
        )

    def decision_for(self, candidate_id: str) -> Decision:
        for decision in self.decisions:
            if decision.candidate_id == candidate_id:
                return decision
        raise KeyError(candidate_id)


@dataclass(frozen=True, slots=True, order=True)
class ResolutionWarning:
    """Non-fatal ambiguity surfaced instead of hidden by a stable tie-break."""

    field: ClaimField
    candidate_ids: tuple[str, str]
    reason: str = "equal-rank-conflicting-claims"


def resolve_candidates(
    candidates: Iterable[Candidate], *, collect_warnings: bool = True
) -> Resolution:
    """Resolve candidates without depending on their input iteration order.

    Higher priority and specificity win.  Remaining ties are settled by source
    coordinates, rule id, and candidate id.  Rules should encode intentional
    precedence in ``priority`` rather than relying on declaration order.
    """

    ordered = tuple(sorted(candidates, key=lambda candidate: candidate.sort_key))
    _ensure_unique_ids(ordered)

    selected: list[Candidate] = []
    scalar_values: dict[ClaimField, object] = {}
    repeatable_values: dict[ClaimField, list[str]] = {
        ClaimField.CODECS: [],
        ClaimField.AUDIO: [],
        ClaimField.TAGS: [],
    }
    decisions: list[Decision] = []

    for candidate in ordered:
        explicit_blocker = _find_explicit_blocker(candidate, selected)
        if explicit_blocker is not None:
            as_title = candidate.preserve_as_title_on_conflict
            decisions.append(
                Decision(
                    candidate_id=candidate.id,
                    status=(
                        DecisionStatus.REJECTED_AS_TITLE
                        if as_title
                        else DecisionStatus.REJECTED_CONFLICT
                    ),
                    reason=f"blocked-by:{explicit_blocker.id}",
                )
            )
            continue

        overlap_blocker = _find_overlap_blocker(candidate, selected)
        if overlap_blocker is not None:
            as_title = candidate.preserve_as_title_on_conflict
            decisions.append(
                Decision(
                    candidate_id=candidate.id,
                    status=(
                        DecisionStatus.REJECTED_AS_TITLE
                        if as_title
                        else DecisionStatus.REJECTED_CONFLICT
                    ),
                    reason=f"overlaps:{overlap_blocker.id}",
                )
            )
            continue

        scalar_items = candidate.claims.scalar_items()
        occupied = tuple(field for field, _ in scalar_items if field in scalar_values)
        if occupied:
            shadowed_excluded_spans: tuple[Span, ...] = ()
            if candidate.shadowed_span_policy is ShadowedSpanPolicy.EXCLUDE:
                shadowed_excluded_spans = (
                    candidate.shadowed_spans
                    if candidate.shadowed_spans is not None
                    else candidate.spans
                )
            decisions.append(
                Decision(
                    candidate_id=candidate.id,
                    status=DecisionStatus.SHADOWED,
                    reason="shadowed-fields:"
                    + ",".join(field.value for field in occupied),
                    excluded_spans=shadowed_excluded_spans,
                )
            )
            continue

        won_fields: list[ClaimField] = []
        for field, value in scalar_items:
            if field not in scalar_values:
                scalar_values[field] = value
                won_fields.append(field)

        for field, values in candidate.claims.repeatable_items():
            target = repeatable_values[field]
            before = len(target)
            for value in values:
                _append_unique_casefold(target, value)
            if len(target) > before:
                won_fields.append(field)

        selected.append(candidate)
        decisions.append(
            Decision(
                candidate_id=candidate.id,
                status=DecisionStatus.SELECTED,
                reason="selected",
                won_fields=tuple(won_fields),
                excluded_spans=candidate.spans,
            )
        )

    decisions_tuple = tuple(decisions)
    warnings = (
        _find_equal_rank_conflicts(ordered, decisions_tuple) if collect_warnings else ()
    )
    excluded_spans = _merge_spans(
        span for decision in decisions_tuple for span in decision.excluded_spans
    )
    evidence = _collect_evidence(ordered, decisions_tuple)

    return Resolution(
        claims=_build_claims(scalar_values, repeatable_values),
        decisions=decisions_tuple,
        excluded_spans=excluded_spans,
        evidence=evidence,
        warnings=warnings,
    )


def _ensure_unique_ids(candidates: tuple[Candidate, ...]) -> None:
    seen: set[str] = set()
    for candidate in candidates:
        if candidate.id in seen:
            raise ValueError(f"duplicate candidate id: {candidate.id}")
        seen.add(candidate.id)


def _find_equal_rank_conflicts(
    candidates: tuple[Candidate, ...],
    decisions: tuple[Decision, ...],
) -> tuple[ResolutionWarning, ...]:
    selected_ids = {
        decision.candidate_id
        for decision in decisions
        if decision.status is DecisionStatus.SELECTED
    }
    warnings: set[ResolutionWarning] = set()
    for left, right in combinations(candidates, 2):
        if (
            left.priority != right.priority
            or left.specificity != right.specificity
            or not ({left.id, right.id} & selected_ids)
        ):
            continue
        left_values = dict(left.claims.scalar_items())
        right_values = dict(right.claims.scalar_items())
        for field in left_values.keys() & right_values.keys():
            if _warning_values_equal(field, left_values[field], right_values[field]):
                continue
            first_id, second_id = sorted((left.id, right.id))
            warnings.add(
                ResolutionWarning(
                    field=field,
                    candidate_ids=(first_id, second_id),
                )
            )
    return tuple(sorted(warnings))


def _warning_values_equal(field: ClaimField, left: object, right: object) -> bool:
    # ``season_raw`` records the spelling that supplied the semantic season;
    # different spellings are provenance, not contradictory values.
    if field is ClaimField.SEASON_RAW:
        return True
    if isinstance(left, str) and isinstance(right, str):
        left_normalized = left.casefold()
        right_normalized = right.casefold()
        if field is ClaimField.SOURCE:
            left_normalized = re.sub(r"[-_.\s]+", "", left_normalized)
            right_normalized = re.sub(r"[-_.\s]+", "", right_normalized)
        return left_normalized == right_normalized
    return left == right


def _find_explicit_blocker(
    candidate: Candidate, selected: list[Candidate]
) -> Candidate | None:
    for winner in selected:
        if (winner.blocks & candidate.conflict_tags) or (
            candidate.blocks & winner.conflict_tags
        ):
            return winner
    return None


def _find_overlap_blocker(
    candidate: Candidate, selected: list[Candidate]
) -> Candidate | None:
    if candidate.overlap_policy is OverlapPolicy.SHARED:
        return None
    for winner in selected:
        if winner.overlap_policy is OverlapPolicy.SHARED:
            continue
        if any(
            span.overlaps(winner_span)
            for span in candidate.spans
            for winner_span in winner.spans
        ):
            return winner
    return None


def _append_unique_casefold(values: list[str], value: str) -> None:
    folded = value.casefold()
    if folded not in {existing.casefold() for existing in values}:
        values.append(value)


def _build_claims(
    scalar_values: dict[ClaimField, object],
    repeatable_values: dict[ClaimField, list[str]],
) -> Claims:
    return Claims(
        group=_scalar(scalar_values, ClaimField.GROUP, str),
        season=_scalar(scalar_values, ClaimField.SEASON, int),
        season_raw=_scalar(scalar_values, ClaimField.SEASON_RAW, str),
        episode=_number_scalar(scalar_values, ClaimField.EPISODE),
        episode_end=_number_scalar(scalar_values, ClaimField.EPISODE_END),
        episode_title=_scalar(scalar_values, ClaimField.EPISODE_TITLE, str),
        media_type=_scalar(scalar_values, ClaimField.MEDIA_TYPE, MediaType),
        release_kind=_scalar(scalar_values, ClaimField.RELEASE_KIND, ReleaseKind),
        resolution=_scalar(scalar_values, ClaimField.RESOLUTION, str),
        source=_scalar(scalar_values, ClaimField.SOURCE, str),
        subtitle=_scalar(scalar_values, ClaimField.SUBTITLE, str),
        codecs=tuple(repeatable_values[ClaimField.CODECS]),
        audio=tuple(repeatable_values[ClaimField.AUDIO]),
        container=_scalar(scalar_values, ClaimField.CONTAINER, str),
        version=_scalar(scalar_values, ClaimField.VERSION, int),
        year=_scalar(scalar_values, ClaimField.YEAR, int),
        tags=tuple(repeatable_values[ClaimField.TAGS]),
    )


def _scalar[T](
    values: dict[ClaimField, object], field: ClaimField, expected: type[T]
) -> T | None:
    value = values.get(field)
    if value is None:
        return None
    if expected is not object and not isinstance(value, expected):
        raise TypeError(f"invalid value for {field.value}: {value!r}")
    return value  # type: ignore[return-value]


def _number_scalar(
    values: dict[ClaimField, object], field: ClaimField
) -> int | float | None:
    value = values.get(field)
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise TypeError(f"invalid value for {field.value}: {value!r}")
    return value


def _merge_spans(spans: Iterable[Span]) -> tuple[Span, ...]:
    ordered = sorted(set(spans))
    if not ordered:
        return ()

    merged: list[Span] = [ordered[0]]
    for span in ordered[1:]:
        previous = merged[-1]
        if span.segment == previous.segment and span.start <= previous.end:
            merged[-1] = Span(
                previous.segment, previous.start, max(previous.end, span.end)
            )
        else:
            merged.append(span)
    return tuple(merged)


def _collect_evidence(
    candidates: tuple[Candidate, ...], decisions: tuple[Decision, ...]
) -> tuple[str, ...]:
    evidence: list[str] = []
    for candidate, decision in zip(candidates, decisions, strict=True):
        if decision.status is not DecisionStatus.SELECTED:
            continue
        for item in candidate.evidence:
            if item not in evidence:
                evidence.append(item)
    return tuple(evidence)
