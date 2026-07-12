from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from module.parser.analyser.tokenizer.candidate import (
    Candidate,
    Claims,
    DecisionStatus,
    Observation,
    Span,
)
from module.parser.analyser.tokenizer.parser import (
    parse_release_title,
    parse_release_title_with_trace,
)
from module.parser.analyser.tokenizer.resolver import resolve_candidates
from module.parser.analyser.tokenizer.result import MediaType
from module.parser.analyser.tokenizer.trace import ParseTrace, TraceSegment


def test_trace_canonicalizes_diagnostic_input_order() -> None:
    early_observation = Observation(
        id="episode-observation",
        rule_id="episode",
        kind="episode",
        span=Span(0, 8, 10),
        text="01",
        captures=("01",),
    )
    late_observation = Observation(
        id="resolution-observation",
        rule_id="resolution",
        kind="resolution",
        span=Span(1, 0, 5),
        text="1080p",
    )
    episode = Candidate(
        id="episode",
        rule_id="episode",
        spans=(early_observation.span,),
        claims=Claims(episode=1),
        priority=90,
        observation_ids=(early_observation.id,),
    )
    resolution_candidate = Candidate(
        id="resolution",
        rule_id="resolution",
        spans=(late_observation.span,),
        claims=Claims(resolution="1080p"),
        priority=10,
        observation_ids=(late_observation.id,),
    )
    candidates = (resolution_candidate, episode)
    resolution = resolve_candidates(candidates)

    trace = ParseTrace.from_resolution(
        raw="Anime - 01 [1080p]",
        normalized="Anime - 01 [1080p]",
        resolution=resolution,
        segments=(
            TraceSegment(1, "1080p", 11, 18, 12, 17, "square"),
            TraceSegment(0, "Anime - 01 ", 0, 11, 0, 11),
        ),
        observations=(late_observation, early_observation),
        candidates=candidates,
        residuals=("Anime", ""),
    )

    assert tuple(segment.index for segment in trace.segments) == (0, 1)
    assert tuple(item.id for item in trace.observations) == (
        "episode-observation",
        "resolution-observation",
    )
    assert tuple(item.id for item in trace.candidates) == ("episode", "resolution")
    assert trace.decision_for("episode").status is DecisionStatus.SELECTED

    attributable_spans = {
        span for decision in trace.decisions for span in decision.excluded_spans
    }
    for excluded in trace.excluded_spans:
        cursor = excluded.start
        for span in sorted(attributable_spans):
            if span.segment != excluded.segment or span.end <= cursor:
                continue
            assert span.start <= cursor
            cursor = max(cursor, span.end)
            if cursor >= excluded.end:
                break
        assert cursor >= excluded.end


def test_trace_exposes_title_rejections_and_is_frozen() -> None:
    winner = Candidate(
        id="movie",
        rule_id="movie",
        spans=(Span(0, 0, 4),),
        claims=Claims(),
        priority=100,
        blocks=frozenset({"ambiguous"}),
    )
    rejected = Candidate(
        id="title-number",
        rule_id="bare-number",
        spans=(Span(0, 8, 9),),
        claims=Claims(episode=0),
        priority=10,
        conflict_tags=frozenset({"ambiguous"}),
        preserve_as_title_on_conflict=True,
    )
    resolution = resolve_candidates((rejected, winner))
    trace = ParseTrace.from_resolution(
        raw="Movie X 0",
        normalized="Movie X 0",
        resolution=resolution,
        candidates=(rejected, winner),
    )

    assert trace.rejected_as_title == ("title-number",)
    with pytest.raises(FrozenInstanceError):
        trace.raw = "changed"  # type: ignore[misc]


def test_trace_missing_candidate_decision_raises_key_error() -> None:
    trace = ParseTrace(raw="Anime", normalized="Anime")

    with pytest.raises(KeyError):
        trace.decision_for("missing")


def test_real_parser_trace_reproduces_public_result_and_accounts_for_masks() -> None:
    raw = "[Group] Anime - 01 [1080p WEB-DL HEVC AAC MKV]"

    outcome = parse_release_title_with_trace(raw)

    assert outcome.result == parse_release_title(raw)
    assert outcome.result is not None
    assert outcome.result.episode == 1
    assert outcome.trace.claims.episode == 1
    assert outcome.result.codecs == ("HEVC",)
    assert outcome.result.audio == ("AAC",)
    assert len(outcome.trace.candidates) == len(outcome.trace.decisions)
    assert {candidate.id for candidate in outcome.trace.candidates} == {
        decision.candidate_id for decision in outcome.trace.decisions
    }

    excluded_source_spans = tuple(
        span for decision in outcome.trace.decisions for span in decision.excluded_spans
    )
    for excluded in outcome.trace.excluded_spans:
        for position in range(excluded.start, excluded.end):
            assert any(
                source.segment == excluded.segment
                and source.start <= position < source.end
                for source in excluded_source_spans
            )


def test_real_parser_trace_preserves_movie_title_number_with_reason() -> None:
    outcome = parse_release_title_with_trace("[Group] 劇場版 86 - 0 [1080p WEB-DL]")

    assert outcome.result is not None
    assert outcome.result.media_type is MediaType.MOVIE
    assert outcome.result.episode is None
    assert outcome.result.title_en == "86 - 0"
    assert any(
        candidate_id.startswith("episode.trailing:")
        for candidate_id in outcome.trace.rejected_as_title
    )


def test_spaced_explicit_range_wins_over_both_single_episode_candidates() -> None:
    raw = "[Group] Anime Title EP01 ~ EP02 [1080p]"

    outcome = parse_release_title_with_trace(raw)

    assert outcome.result == parse_release_title(raw)
    assert outcome.result is not None
    assert outcome.result.episode == 1
    assert outcome.result.episode_end == 2
    range_candidate = next(
        candidate
        for candidate in outcome.trace.candidates
        if candidate.rule_id == "episode.range"
    )
    explicit_candidates = tuple(
        candidate
        for candidate in outcome.trace.candidates
        if candidate.rule_id == "episode.explicit"
    )
    assert (
        outcome.trace.decision_for(range_candidate.id).status is DecisionStatus.SELECTED
    )
    assert len(explicit_candidates) == 2
    assert all(
        outcome.trace.decision_for(candidate.id).status
        is DecisionStatus.REJECTED_CONFLICT
        for candidate in explicit_candidates
    )
    assert outcome.trace.warnings == ()


def test_mixed_collection_candidate_shadows_embedded_ova_and_range() -> None:
    raw = "[Group] Anime Title [TV 01-12 + OVA 01-02] [1080p]"

    outcome = parse_release_title_with_trace(raw)

    assert outcome.result is not None
    assert outcome.result.is_mixed_collection
    mixed = next(
        candidate
        for candidate in outcome.trace.candidates
        if candidate.rule_id == "cardinality.mixed-content"
    )
    embedded = tuple(
        candidate
        for candidate in outcome.trace.candidates
        if candidate.rule_id in {"episode.range", "episode.ova-range", "media.ova"}
    )
    assert outcome.trace.decision_for(mixed.id).status is DecisionStatus.SELECTED
    assert embedded
    assert all(
        outcome.trace.decision_for(candidate.id).status
        is DecisionStatus.REJECTED_CONFLICT
        for candidate in embedded
    )


def test_mixed_public_result_normalizes_external_episode_resolution() -> None:
    outcome = parse_release_title_with_trace("[TV + OVA] Anime Title - 01 [1080p]")

    assert outcome.result is not None
    assert outcome.result.is_mixed_collection
    assert outcome.result.episode is None
    assert "episode" not in outcome.result.evidence
    assert outcome.trace.claims.episode == 1


def test_mixed_numeric_title_retry_keeps_resolver_residuals_consistent() -> None:
    outcome = parse_release_title_with_trace("[TV+OVA] 86 [1080p]")

    assert outcome.result is not None
    assert outcome.result.primary_title == "86"
    for span in outcome.trace.excluded_spans:
        residual = outcome.trace.residuals[span.segment]
        assert not residual[span.start : span.end].strip()


def test_empty_input_still_returns_an_explainable_outcome() -> None:
    outcome = parse_release_title_with_trace("  ")

    assert outcome.result is None
    assert outcome.trace.raw == "  "
    assert outcome.trace.normalized == ""
    assert outcome.trace.candidates == ()
    assert outcome.trace.decisions == ()


@pytest.mark.parametrize(
    "raw",
    (
        "Anime S01E01 Season 1 Episode 1 [1080p]",
        "Anime - 01 [1080p][1080P]",
        "Anime - 01 [WEB-DL][web_dl]",
    ),
)
def test_equivalent_spellings_do_not_emit_ambiguity_warnings(raw: str) -> None:
    outcome = parse_release_title_with_trace(raw)

    assert outcome.result is not None
    assert outcome.trace.warnings == ()


@pytest.mark.parametrize(
    "raw",
    (
        "[Group] Anime (Alt [Nested]) - 01 [1080p]",
        "[Group] Anime - 01 [1080p",
    ),
)
def test_nested_or_unclosed_segment_coordinates_remain_valid(raw: str) -> None:
    outcome = parse_release_title_with_trace(raw)

    assert outcome.result is not None
    for segment in outcome.trace.segments:
        assert (
            outcome.trace.normalized[segment.content_start : segment.content_end]
            == segment.text
        )
        assert segment.outer_start <= segment.content_start
        assert segment.content_end <= segment.outer_end
