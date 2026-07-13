"""Golden-corpus regression tests for release-title parsing.

The fixture snapshots only the public generic result and the legacy adapter.
Parser evidence and trace data are deliberately excluded so internal rule and
resolver changes do not create meaningless snapshot churn.
"""

from __future__ import annotations

import json
from dataclasses import asdict, fields
from enum import Enum
from pathlib import Path
from typing import Any

import pytest

from module.parser.analyser.raw_parser import raw_parser
from module.parser.analyser.tokenizer import (
    parse_release_title,
    parse_release_title_with_trace,
)

_CORPUS_PATH = Path(__file__).parent / "fixtures" / "release_title_golden.json"
_CORPUS_SIZE = 71

_GENERIC_DEFAULTS: dict[str, Any] = {
    "title_en": None,
    "title_zh": None,
    "title_jp": None,
    "group": None,
    "season": None,
    "season_raw": None,
    "episode": None,
    "episode_end": None,
    "episode_title": None,
    "media_type": "unknown",
    "release_kind": "single",
    "resolution": None,
    "source": None,
    "subtitle": None,
    "codecs": [],
    "audio": [],
    "container": None,
    "version": None,
    "year": None,
    "tags": [],
}


def _load_corpus() -> dict[str, Any]:
    with _CORPUS_PATH.open(encoding="utf-8") as corpus_file:
        return json.load(corpus_file)


_CORPUS = _load_corpus()
_CASES = _CORPUS["cases"]


def _case_params() -> list[Any]:
    return [pytest.param(case, id=case["id"]) for case in _CASES]


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return list(value)
    return value


def _generic_snapshot(parsed: Any) -> dict[str, Any]:
    return {
        field_name: _json_value(getattr(parsed, field_name))
        for field_name in _GENERIC_DEFAULTS
    }


def _expected_generic(case: dict[str, Any]) -> dict[str, Any] | None:
    overrides = case["expected"]
    if overrides is None:
        return None
    return {**_GENERIC_DEFAULTS, **overrides}


def test_golden_corpus_integrity() -> None:
    assert _CORPUS["schema_version"] == 1
    assert len(_CASES) == _CORPUS_SIZE

    ids = [case["id"] for case in _CASES]
    raw_titles = [case["raw"] for case in _CASES]
    identities = [(case["category"], case["id"], case["raw"]) for case in _CASES]

    assert len(ids) == len(set(ids))
    assert len(raw_titles) == len(set(raw_titles))
    assert len(identities) == len(set(identities))
    assert all(case["category"] for case in _CASES)
    assert all("evidence" not in case for case in _CASES)
    assert all(
        case["expected"] is None or "evidence" not in case["expected"]
        for case in _CASES
    )
    assert all("trace" not in case for case in _CASES)


@pytest.mark.parametrize("case", _case_params())
def test_generic_parser_matches_golden_corpus(case: dict[str, Any]) -> None:
    parsed = parse_release_title(case["raw"])
    expected = _expected_generic(case)

    if expected is None:
        assert parsed is None
        return

    assert parsed is not None
    assert parsed.raw == case["raw"]
    public_fields = {
        field.name for field in fields(parsed) if field.name not in {"raw", "evidence"}
    }
    assert public_fields == set(_GENERIC_DEFAULTS)
    assert _generic_snapshot(parsed) == expected


@pytest.mark.parametrize("case", _case_params())
def test_legacy_parser_matches_golden_corpus(case: dict[str, Any]) -> None:
    parsed = raw_parser(case["raw"])
    expected = case["legacy"]

    if expected is None:
        assert parsed is None
        return

    assert parsed is not None
    assert asdict(parsed) == expected


@pytest.mark.parametrize("case", _case_params())
def test_traced_parser_matches_plain_result_and_has_valid_references(
    case: dict[str, Any],
) -> None:
    outcome = parse_release_title_with_trace(case["raw"])

    assert outcome.result == parse_release_title(case["raw"])
    candidate_ids = {candidate.id for candidate in outcome.trace.candidates}
    observation_ids = {observation.id for observation in outcome.trace.observations}
    assert {decision.candidate_id for decision in outcome.trace.decisions} == (
        candidate_ids
    )
    assert {
        observation_id
        for candidate in outcome.trace.candidates
        for observation_id in candidate.observation_ids
    } == observation_ids
    for span in (
        span for candidate in outcome.trace.candidates for span in candidate.spans
    ):
        assert 0 <= span.segment < len(outcome.trace.segments)
        assert (
            0 <= span.start < span.end <= len(outcome.trace.segments[span.segment].text)
        )
