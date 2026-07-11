from __future__ import annotations

from itertools import permutations

import pytest

from module.parser.analyser.tokenizer.candidate import (
    Candidate,
    ClaimField,
    Claims,
    DecisionStatus,
    OverlapPolicy,
    ShadowedSpanPolicy,
    Span,
)
from module.parser.analyser.tokenizer.resolver import resolve_candidates
from module.parser.analyser.tokenizer.result import MediaType


def _candidate(
    candidate_id: str,
    *,
    start: int,
    end: int,
    claims: Claims,
    priority: int,
    **kwargs: object,
) -> Candidate:
    return Candidate(
        id=candidate_id,
        rule_id=candidate_id,
        spans=(Span(0, start, end),),
        claims=claims,
        priority=priority,
        **kwargs,  # type: ignore[arg-type]
    )


def test_span_is_half_open_and_validated() -> None:
    assert Span(0, 1, 4).length == 3
    assert Span(0, 1, 4).overlaps(Span(0, 3, 5))
    assert not Span(0, 1, 4).overlaps(Span(0, 4, 5))
    assert not Span(0, 1, 4).overlaps(Span(1, 1, 4))
    assert Span(0, 1, 4).contains(Span(0, 2, 3))

    with pytest.raises(ValueError):
        Span(0, 3, 3)


def test_resolution_is_independent_of_input_order() -> None:
    explicit = _candidate(
        "explicit",
        start=10,
        end=16,
        claims=Claims(season=2, episode=5),
        priority=100,
        evidence=("season", "episode"),
    )
    trailing = _candidate(
        "trailing",
        start=20,
        end=22,
        claims=Claims(episode=99),
        priority=70,
        evidence=("episode",),
    )

    resolutions = [
        resolve_candidates(order) for order in permutations((trailing, explicit))
    ]

    assert resolutions[0] == resolutions[1]
    result = resolutions[0]
    assert result.claims.season == 2
    assert result.claims.episode == 5
    assert result.decision_for("explicit").status is DecisionStatus.SELECTED
    shadowed = result.decision_for("trailing")
    assert shadowed.status is DecisionStatus.SHADOWED
    assert shadowed.exclude_from_title
    assert result.excluded_spans == (Span(0, 10, 16), Span(0, 20, 22))


def test_movie_rejects_ambiguous_number_as_title_without_masking_it() -> None:
    movie = _candidate(
        "movie",
        start=0,
        end=4,
        claims=Claims(media_type=MediaType.MOVIE),
        priority=100,
        blocks=frozenset({"ambiguous-episode"}),
        evidence=("movie",),
    )
    title_number = _candidate(
        "trailing-number",
        start=12,
        end=13,
        claims=Claims(episode=0),
        priority=70,
        conflict_tags=frozenset({"ambiguous-episode"}),
        preserve_as_title_on_conflict=True,
    )

    result = resolve_candidates((title_number, movie))

    assert result.claims.media_type is MediaType.MOVIE
    assert result.claims.episode is None
    decision = result.decision_for("trailing-number")
    assert decision.status is DecisionStatus.REJECTED_AS_TITLE
    assert not decision.exclude_from_title
    assert result.excluded_spans == (Span(0, 0, 4),)


def test_overlapping_shadowed_field_reports_conflict_without_extra_mask() -> None:
    combined = _candidate(
        "combined",
        start=2,
        end=10,
        claims=Claims(subtitle="GB", container="MKV"),
        priority=80,
        specificity=2,
    )
    container = _candidate(
        "container",
        start=5,
        end=10,
        claims=Claims(container="MKV"),
        priority=70,
    )

    result = resolve_candidates((container, combined))

    assert result.claims.subtitle == "GB"
    assert result.claims.container == "MKV"
    rejected = result.decision_for("container")
    assert rejected.status is DecisionStatus.REJECTED_CONFLICT
    assert result.excluded_spans == (Span(0, 2, 10),)


def test_partially_overlapping_same_field_does_not_mask_loser_only_text() -> None:
    winner = _candidate(
        "winner", start=2, end=10, claims=Claims(episode=1), priority=80
    )
    partial_loser = _candidate(
        "partial-loser", start=8, end=16, claims=Claims(episode=2), priority=70
    )

    result = resolve_candidates((partial_loser, winner))

    assert result.claims.episode == 1
    assert (
        result.decision_for("partial-loser").status is DecisionStatus.REJECTED_CONFLICT
    )
    assert result.excluded_spans == (Span(0, 2, 10),)


def test_different_fields_on_overlapping_exclusive_spans_are_rejected() -> None:
    source = _candidate(
        "source",
        start=0,
        end=6,
        claims=Claims(source="WEB-DL"),
        priority=80,
    )
    codec = _candidate(
        "codec",
        start=4,
        end=8,
        claims=Claims(codecs=("HEVC",)),
        priority=70,
    )

    result = resolve_candidates((codec, source))

    assert result.claims.source == "WEB-DL"
    assert result.claims.codecs == ()
    assert result.decision_for("codec").status is DecisionStatus.REJECTED_CONFLICT


def test_shared_overlay_allows_explicit_transparent_overlap() -> None:
    overlay = _candidate(
        "overlay",
        start=0,
        end=12,
        claims=Claims(tags=("dub",)),
        priority=80,
        overlap_policy=OverlapPolicy.SHARED,
    )
    resolution = _candidate(
        "resolution",
        start=2,
        end=7,
        claims=Claims(resolution="1080p"),
        priority=70,
    )

    result = resolve_candidates((resolution, overlay))

    assert result.claims.tags == ("dub",)
    assert result.claims.resolution == "1080p"
    assert result.decision_for("overlay").status is DecisionStatus.SELECTED
    assert result.decision_for("resolution").status is DecisionStatus.SELECTED


def test_shadowed_candidate_can_keep_its_span_in_title() -> None:
    strong = _candidate(
        "strong",
        start=0,
        end=4,
        claims=Claims(episode=1),
        priority=100,
    )
    ambiguous = _candidate(
        "ambiguous",
        start=8,
        end=9,
        claims=Claims(episode=2),
        priority=70,
        shadowed_span_policy=ShadowedSpanPolicy.KEEP,
    )

    result = resolve_candidates((ambiguous, strong))

    assert result.decision_for("ambiguous").status is DecisionStatus.SHADOWED
    assert result.excluded_spans == (Span(0, 0, 4),)


def test_shadowed_candidate_excludes_marker_but_keeps_dependent_span() -> None:
    winner = _candidate(
        "winner", start=0, end=4, claims=Claims(episode=1), priority=100
    )
    marker = Span(0, 8, 12)
    dependent_title = Span(0, 12, 24)
    loser = Candidate(
        id="loser",
        rule_id="loser",
        spans=(marker, dependent_title),
        shadowed_spans=(marker,),
        claims=Claims(episode=2, episode_title="Dependent title"),
        priority=70,
    )

    result = resolve_candidates((loser, winner))

    decision = result.decision_for("loser")
    assert decision.status is DecisionStatus.SHADOWED
    assert decision.excluded_spans == (marker,)
    assert result.excluded_spans == (Span(0, 0, 4), marker)


def test_repeatable_claims_are_case_insensitively_deduplicated() -> None:
    first = _candidate(
        "codec-a",
        start=0,
        end=4,
        claims=Claims(codecs=("HEVC",), tags=("tag-a",)),
        priority=10,
    )
    second = _candidate(
        "codec-b",
        start=5,
        end=9,
        claims=Claims(codecs=("hevc", "AVC"), tags=("TAG-A",)),
        priority=10,
    )

    result = resolve_candidates((second, first))

    assert result.claims.codecs == ("HEVC", "AVC")
    assert result.claims.tags == ("tag-a",)
    assert ClaimField.CODECS in result.decision_for("codec-a").won_fields


def test_duplicate_candidate_ids_are_rejected() -> None:
    first = _candidate(
        "duplicate", start=0, end=1, claims=Claims(episode=1), priority=1
    )
    second = _candidate(
        "duplicate", start=2, end=3, claims=Claims(episode=2), priority=2
    )

    with pytest.raises(ValueError, match="duplicate candidate id"):
        resolve_candidates((first, second))


def test_equal_priority_conflicting_claims_emit_stable_warning() -> None:
    first = _candidate(
        "episode-a", start=0, end=2, claims=Claims(episode=1), priority=70
    )
    second = _candidate(
        "episode-b", start=4, end=6, claims=Claims(episode=2), priority=70
    )

    forward = resolve_candidates((first, second))
    reverse = resolve_candidates((second, first))

    assert forward == reverse
    assert len(forward.warnings) == 1
    assert forward.warnings[0].field is ClaimField.EPISODE
    assert forward.warnings[0].candidate_ids == ("episode-a", "episode-b")


def test_specificity_resolves_same_priority_without_ambiguity_warning() -> None:
    explicit = _candidate(
        "explicit",
        start=0,
        end=2,
        claims=Claims(episode=1),
        priority=70,
        specificity=2,
    )
    generic = _candidate(
        "generic", start=4, end=6, claims=Claims(episode=2), priority=70
    )

    result = resolve_candidates((generic, explicit))

    assert result.claims.episode == 1
    assert result.warnings == ()


def test_fully_shadowed_low_priority_tie_does_not_warn() -> None:
    winner = _candidate(
        "winner", start=0, end=2, claims=Claims(episode=1), priority=100
    )
    low_a = _candidate("low-a", start=4, end=6, claims=Claims(episode=2), priority=70)
    low_b = _candidate("low-b", start=8, end=10, claims=Claims(episode=3), priority=70)

    result = resolve_candidates((low_b, winner, low_a))

    assert result.claims.episode == 1
    assert result.warnings == ()
