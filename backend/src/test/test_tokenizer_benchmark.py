"""Fast correctness tests for the tokenizer benchmark harness.

These tests validate corpus handling and statistics only.  They intentionally
contain no wall-clock threshold and do not turn normal pytest runs into a
performance gate.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from module.parser.analyser.tokenizer.benchmark import (
    BenchmarkCase,
    BenchmarkGroup,
    benchmark_group,
    calibrate_loops,
    load_corpus,
    real_groups,
    run_benchmark,
    run_samples,
    stress_groups,
    summarize_samples,
)

_BACKEND_ROOT = Path(__file__).parents[2]
_REPO_ROOT = _BACKEND_ROOT.parent
_CORPUS_PATH = Path(__file__).parent / "fixtures" / "release_title_golden.json"


def test_load_corpus_and_real_group_partitions() -> None:
    corpus = load_corpus(_CORPUS_PATH)
    groups = {group.name: group for group in real_groups(corpus)}

    assert corpus.schema_version == 1
    assert len(corpus.cases) == 71
    assert len(corpus.sha256) == 64
    assert {name: len(group.cases) for name, group in groups.items()} == {
        "all-real": 71,
        "episode": 21,
        "cardinality": 10,
        "media": 22,
        "ambiguous": 15,
        "technical": 3,
    }


def test_load_corpus_rejects_duplicate_resource_names(tmp_path: Path) -> None:
    corpus_path = tmp_path / "duplicate.json"
    corpus_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "cases": [
                    {"id": "first", "category": "episode", "raw": "Same"},
                    {"id": "second", "category": "movie", "raw": "Same"},
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="raw titles must be unique"):
        load_corpus(corpus_path)


def test_calibrate_loops_grows_until_target_duration() -> None:
    ticks = iter((0, 10, 0, 80, 0, 160))
    calls: list[str] = []

    loops = calibrate_loops(
        lambda title: calls.append(title),
        ("title",),
        100,
        clock=lambda: next(ticks),
    )

    assert loops == 20
    assert len(calls) == 31


def test_run_samples_normalizes_whole_batch_operations() -> None:
    ticks = iter((10, 110, 200, 500))
    calls: list[str] = []

    elapsed = run_samples(
        lambda title: calls.append(title),
        ("first", "second"),
        loops=2,
        samples=2,
        clock=lambda: next(ticks),
    )

    assert elapsed == (100, 300)
    assert calls == ["first", "second"] * 4


def test_benchmark_group_rejects_non_positive_fixed_loops() -> None:
    group = BenchmarkGroup(
        name="invalid",
        description="invalid fixed loop count",
        cases=(BenchmarkCase("case", "episode", "Anime - 01"),),
    )

    with pytest.raises(ValueError, match="fixed loops must be positive"):
        benchmark_group(
            lambda _title: None,
            group,
            warmup_rounds=0,
            samples=1,
            target_ns=1,
            loops=0,
        )


def test_summarize_samples_uses_nearest_rank_p95() -> None:
    summary = summarize_samples((200, 400, 600, 800), operations_per_sample=2)

    assert summary["sample_elapsed_ns"] == [200, 400, 600, 800]
    assert summary["ns_per_title"] == {
        "min": 100,
        "mean": 250,
        "median": 250.0,
        "p95": 400,
        "max": 400,
        "mad": 100.0,
        "mad_percent": 40.0,
    }
    assert summary["titles_per_second"] == 4_000_000


def test_stress_groups_cover_scaling_and_conflicts() -> None:
    groups = stress_groups()

    assert [group.name for group in groups] == [
        "stress-tags-1",
        "stress-tags-4",
        "stress-tags-16",
        "stress-tags-64",
        "stress-conflicts",
    ]
    lengths = [len(group.cases[0].raw) for group in groups[:4]]
    assert lengths == sorted(lengths)
    assert len(set(lengths)) == 4


def test_fixed_loop_report_is_json_serializable_without_speed_assertions() -> None:
    corpus = load_corpus(_CORPUS_PATH)

    report = run_benchmark(
        corpus,
        repo_root=_REPO_ROOT,
        modes=("plain", "trace"),
        suite="stress",
        warmup_rounds=0,
        samples=1,
        target_ns=1,
        loops=1,
    )

    assert report["schema_version"] == 1
    assert report["benchmark"] == "release-title-tokenizer"
    assert set(report["results"]) == {"plain", "trace"}
    assert set(report["comparison"]) == {
        "stress-tags-1",
        "stress-tags-4",
        "stress-tags-16",
        "stress-tags-64",
        "stress-conflicts",
    }
    json.dumps(report)
