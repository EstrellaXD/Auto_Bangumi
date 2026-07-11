"""Reusable benchmark helpers for the release-title tokenizer.

The benchmark deliberately uses only the standard library.  It measures whole
corpus batches so the timer overhead stays negligible and never treats a noisy
wall-clock result as a correctness or CI pass/fail condition.
"""

from __future__ import annotations

import gc
import hashlib
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .parser import parse_release_title, parse_release_title_with_trace

Parser = Callable[[str], object]
Clock = Callable[[], int]
Progress = Callable[[str], None]


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    """One stable resource name and its semantic corpus category."""

    id: str
    category: str
    raw: str


@dataclass(frozen=True, slots=True)
class BenchmarkCorpus:
    """Validated corpus metadata and cases."""

    path: str
    schema_version: int
    sha256: str
    cases: tuple[BenchmarkCase, ...]


@dataclass(frozen=True, slots=True)
class BenchmarkGroup:
    """Cases timed together as one calibrated benchmark."""

    name: str
    description: str
    cases: tuple[BenchmarkCase, ...]


REAL_GROUPS: tuple[tuple[str, str, frozenset[str]], ...] = (
    ("episode", "ordinary and season-aware episodes", frozenset({"episode"})),
    (
        "cardinality",
        "ranges, batches, and collections",
        frozenset({"range", "batch", "collection"}),
    ),
    (
        "media",
        "movies, specials, and auxiliary media",
        frozenset({"movie", "special", "auxiliary"}),
    ),
    (
        "ambiguous",
        "ambiguous, title-only, negative, and compatibility boundaries",
        frozenset({"ambiguity", "title-only", "negative", "legacy-boundary"}),
    ),
    ("technical", "technical-metadata-heavy titles", frozenset({"technical"})),
)


def load_corpus(path: Path) -> BenchmarkCorpus:
    """Load and validate the release-title golden corpus."""
    try:
        raw_bytes = path.read_bytes()
        payload = json.loads(raw_bytes)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load benchmark corpus {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("benchmark corpus root must be an object")
    schema_version = payload.get("schema_version")
    raw_cases = payload.get("cases")
    if not isinstance(schema_version, int):
        raise ValueError("benchmark corpus schema_version must be an integer")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("benchmark corpus cases must be a non-empty list")

    cases: list[BenchmarkCase] = []
    for index, item in enumerate(raw_cases):
        if not isinstance(item, dict):
            raise ValueError(f"benchmark corpus case {index} must be an object")
        case_id = item.get("id")
        category = item.get("category")
        raw = item.get("raw")
        if not (
            isinstance(case_id, str)
            and case_id
            and isinstance(category, str)
            and category
            and isinstance(raw, str)
            and raw
        ):
            raise ValueError(
                f"benchmark corpus case {index} needs non-empty id/category/raw"
            )
        cases.append(BenchmarkCase(case_id, category, raw))

    ids = [case.id for case in cases]
    titles = [case.raw for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("benchmark corpus case ids must be unique")
    if len(titles) != len(set(titles)):
        raise ValueError("benchmark corpus raw titles must be unique")

    return BenchmarkCorpus(
        path=str(path.resolve()),
        schema_version=schema_version,
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
        cases=tuple(cases),
    )


def real_groups(corpus: BenchmarkCorpus) -> tuple[BenchmarkGroup, ...]:
    """Build a complete real-corpus group plus stable semantic partitions."""
    groups = [
        BenchmarkGroup(
            name="all-real",
            description="all real golden-corpus resource names",
            cases=corpus.cases,
        )
    ]
    covered: set[str] = set()
    for name, description, categories in REAL_GROUPS:
        cases = tuple(case for case in corpus.cases if case.category in categories)
        if cases:
            groups.append(BenchmarkGroup(name, description, cases))
            covered.update(case.category for case in cases)

    all_categories = {case.category for case in corpus.cases}
    uncovered = all_categories - covered
    if uncovered:
        cases = tuple(case for case in corpus.cases if case.category in uncovered)
        groups.append(
            BenchmarkGroup(
                name="other",
                description="new corpus categories not in the stable partitions",
                cases=cases,
            )
        )
    return tuple(groups)


def _technical_stress_title(tag_count: int) -> str:
    tags = ("1080p", "WEB-DL", "HEVC", "AAC")
    suffix = " ".join(f"[{tags[index % len(tags)]}]" for index in range(tag_count))
    return f"[Stress] Benchmark Anime S02E05 {suffix}"


def stress_groups() -> tuple[BenchmarkGroup, ...]:
    """Return fixed synthetic cases for observing parser scaling."""
    groups: list[BenchmarkGroup] = []
    for tag_count in (1, 4, 16, 64):
        case = BenchmarkCase(
            id=f"technical_tags_{tag_count}",
            category="stress",
            raw=_technical_stress_title(tag_count),
        )
        groups.append(
            BenchmarkGroup(
                name=f"stress-tags-{tag_count}",
                description=f"one title containing {tag_count} technical tags",
                cases=(case,),
            )
        )

    conflicts = BenchmarkCase(
        id="conflicting_markers",
        category="stress",
        raw=(
            "[Stress] Benchmark Anime S02E05 E06 07 OVA08 OAD09 SP10 PV11 "
            "Movie 2024 [1080p WEB-DL HEVC AAC]"
        ),
    )
    groups.append(
        BenchmarkGroup(
            name="stress-conflicts",
            description="one title containing overlapping structural/media markers",
            cases=(conflicts,),
        )
    )
    return tuple(groups)


def validate_parser_equivalence(groups: Sequence[BenchmarkGroup]) -> None:
    """Fail before timing if plain and diagnostic APIs disagree."""
    seen: set[str] = set()
    for group in groups:
        for case in group.cases:
            if case.raw in seen:
                continue
            seen.add(case.raw)
            plain = parse_release_title(case.raw)
            traced = parse_release_title_with_trace(case.raw)
            if traced.result != plain:
                raise ValueError(
                    f"plain/trace result mismatch for benchmark case {case.id!r}"
                )


def _execute_batch(parser: Parser, titles: Sequence[str], loops: int) -> object:
    last_result: object = None
    for _ in range(loops):
        for title in titles:
            last_result = parser(title)
    return last_result


def warm_up(parser: Parser, titles: Sequence[str], rounds: int) -> None:
    """Warm regex caches and interpreter paths outside the timed samples."""
    if rounds < 0:
        raise ValueError("warm-up rounds cannot be negative")
    _execute_batch(parser, titles, rounds)


def calibrate_loops(
    parser: Parser,
    titles: Sequence[str],
    target_ns: int,
    *,
    clock: Clock = time.perf_counter_ns,
    maximum_loops: int = 1_048_576,
) -> int:
    """Find a batch loop count that reaches the requested sample duration."""
    if not titles:
        raise ValueError("cannot calibrate an empty benchmark group")
    if target_ns <= 0:
        raise ValueError("target sample duration must be positive")

    loops = 1
    while True:
        gc.collect()
        started = clock()
        _execute_batch(parser, titles, loops)
        elapsed = clock() - started
        if elapsed >= target_ns:
            return loops
        if loops >= maximum_loops:
            raise RuntimeError("benchmark calibration exceeded maximum loop count")

        multiplier = max(2, min(16, math.ceil(target_ns / max(elapsed, 1))))
        loops = min(maximum_loops, loops * multiplier)


def run_samples(
    parser: Parser,
    titles: Sequence[str],
    *,
    loops: int,
    samples: int,
    clock: Clock = time.perf_counter_ns,
) -> tuple[int, ...]:
    """Measure calibrated whole-corpus samples with GC enabled."""
    if not titles:
        raise ValueError("cannot benchmark an empty title sequence")
    if loops <= 0 or samples <= 0:
        raise ValueError("loops and samples must be positive")

    elapsed_samples: list[int] = []
    for _ in range(samples):
        gc.collect()
        started = clock()
        _execute_batch(parser, titles, loops)
        elapsed = clock() - started
        if elapsed < 0:
            raise RuntimeError("benchmark clock moved backwards")
        elapsed_samples.append(elapsed)
    return tuple(elapsed_samples)


def _nearest_rank(values: Sequence[float], percentile: float) -> float:
    if not values:
        raise ValueError("cannot summarize empty benchmark samples")
    if not 0 < percentile <= 1:
        raise ValueError("percentile must be within (0, 1]")
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def summarize_samples(
    elapsed_samples_ns: Sequence[int], operations_per_sample: int
) -> dict[str, Any]:
    """Summarize raw batch timings as stable per-title statistics."""
    if operations_per_sample <= 0:
        raise ValueError("operations_per_sample must be positive")
    if not elapsed_samples_ns:
        raise ValueError("elapsed_samples_ns cannot be empty")

    per_title = [elapsed / operations_per_sample for elapsed in elapsed_samples_ns]
    median = statistics.median(per_title)
    mad = statistics.median(abs(value - median) for value in per_title)
    return {
        "sample_elapsed_ns": list(elapsed_samples_ns),
        "ns_per_title": {
            "min": min(per_title),
            "mean": statistics.fmean(per_title),
            "median": median,
            "p95": _nearest_rank(per_title, 0.95),
            "max": max(per_title),
            "mad": mad,
            "mad_percent": (mad / median * 100) if median else 0.0,
        },
        "titles_per_second": (1_000_000_000 / median) if median else None,
    }


def benchmark_group(
    parser: Parser,
    group: BenchmarkGroup,
    *,
    warmup_rounds: int,
    samples: int,
    target_ns: int,
    loops: int | None = None,
) -> dict[str, Any]:
    """Warm, calibrate, and measure one parser/group pair."""
    if loops is not None and loops <= 0:
        raise ValueError("fixed loops must be positive")
    titles = tuple(case.raw for case in group.cases)
    warm_up(parser, titles, warmup_rounds)
    calibrated_loops = (
        loops if loops is not None else calibrate_loops(parser, titles, target_ns)
    )
    elapsed = run_samples(
        parser,
        titles,
        loops=calibrated_loops,
        samples=samples,
    )
    operations = calibrated_loops * len(titles)
    return {
        "description": group.description,
        "case_count": len(titles),
        "loops": calibrated_loops,
        "operations_per_sample": operations,
        **summarize_samples(elapsed, operations),
    }


def runtime_metadata(repo_root: Path) -> dict[str, Any]:
    """Collect comparison context without making benchmark success depend on Git."""
    metadata: dict[str, Any] = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "python_hash_seed": os.environ.get("PYTHONHASHSEED"),
    }
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout
        )
        metadata.update({"git_commit": commit, "git_dirty": dirty})
    except (OSError, subprocess.SubprocessError):
        metadata.update({"git_commit": None, "git_dirty": None})
    return metadata


def run_benchmark(
    corpus: BenchmarkCorpus,
    *,
    repo_root: Path,
    modes: Sequence[str],
    suite: str,
    warmup_rounds: int,
    samples: int,
    target_ns: int,
    loops: int | None = None,
    progress: Progress | None = None,
) -> dict[str, Any]:
    """Run selected suites and return a JSON-serializable versioned report."""
    if suite not in {"real", "stress", "all"}:
        raise ValueError(f"unsupported benchmark suite: {suite}")
    parsers: dict[str, Parser] = {
        "plain": parse_release_title,
        "trace": parse_release_title_with_trace,
    }
    unknown_modes = set(modes) - parsers.keys()
    if not modes or unknown_modes:
        raise ValueError(f"unsupported benchmark modes: {sorted(unknown_modes)}")

    groups: list[BenchmarkGroup] = []
    if suite in {"real", "all"}:
        groups.extend(real_groups(corpus))
    if suite in {"stress", "all"}:
        groups.extend(stress_groups())
    validate_parser_equivalence(groups)

    results: dict[str, dict[str, Any]] = {}
    for mode in modes:
        mode_results: dict[str, Any] = {}
        for group in groups:
            if progress:
                progress(f"{mode}: {group.name} ({len(group.cases)} cases)")
            mode_results[group.name] = benchmark_group(
                parsers[mode],
                group,
                warmup_rounds=warmup_rounds,
                samples=samples,
                target_ns=target_ns,
                loops=loops,
            )
        results[mode] = mode_results

    comparison: dict[str, Any] = {}
    if {"plain", "trace"}.issubset(results):
        for group in groups:
            plain_ns = results["plain"][group.name]["ns_per_title"]["median"]
            trace_ns = results["trace"][group.name]["ns_per_title"]["median"]
            comparison[group.name] = {
                "trace_overhead_ratio": trace_ns / plain_ns if plain_ns else None,
                "trace_overhead_percent": (
                    (trace_ns - plain_ns) / plain_ns * 100 if plain_ns else None
                ),
            }

    return {
        "schema_version": 1,
        "benchmark": "release-title-tokenizer",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "corpus": {
            "path": corpus.path,
            "schema_version": corpus.schema_version,
            "case_count": len(corpus.cases),
            "sha256": corpus.sha256,
            "categories": dict(
                sorted(Counter(case.category for case in corpus.cases).items())
            ),
        },
        "runtime": runtime_metadata(repo_root),
        "config": {
            "modes": list(modes),
            "suite": suite,
            "warmup_rounds": warmup_rounds,
            "samples": samples,
            "target_sample_ms": target_ns / 1_000_000,
            "fixed_loops": loops,
            "gc_enabled": gc.isenabled(),
        },
        "results": results,
        "comparison": comparison,
    }


def render_text(report: dict[str, Any]) -> str:
    """Render a compact human-readable table from a benchmark report."""
    runtime = report["runtime"]
    corpus = report["corpus"]
    config = report["config"]
    timing = (
        f"fixed loops {config['fixed_loops']}"
        if config["fixed_loops"] is not None
        else f"target {config['target_sample_ms']:g} ms"
    )
    lines = [
        "AutoBangumi release-title tokenizer benchmark",
        (
            f"Python {runtime['python']} ({runtime['implementation']}) | "
            f"{runtime['machine']} | commit {runtime.get('git_commit') or 'unknown'}"
        ),
        (
            f"Corpus {corpus['case_count']} real cases | suite {config['suite']} | "
            f"warmup {config['warmup_rounds']} | samples {config['samples']} | "
            f"{timing}"
        ),
    ]
    if runtime.get("git_dirty"):
        lines.append("Warning: worktree is dirty; record this when comparing runs.")

    for mode, groups in report["results"].items():
        lines.extend(
            [
                "",
                f"{mode.upper()}",
                (
                    f"{'group':<22} {'cases':>5} {'loops':>7} "
                    f"{'median us':>11} {'p95 us':>10} {'MAD %':>8} {'titles/s':>10}"
                ),
            ]
        )
        for name, result in groups.items():
            stats = result["ns_per_title"]
            lines.append(
                f"{name:<22} {result['case_count']:>5} {result['loops']:>7} "
                f"{stats['median'] / 1_000:>11.2f} "
                f"{stats['p95'] / 1_000:>10.2f} "
                f"{stats['mad_percent']:>8.2f} "
                f"{result['titles_per_second']:>10.0f}"
            )

    if report["comparison"]:
        lines.extend(
            [
                "",
                "TRACE OVERHEAD",
                f"{'group':<22} {'ratio':>9} {'overhead':>10}",
            ]
        )
        for name, comparison in report["comparison"].items():
            lines.append(
                f"{name:<22} {comparison['trace_overhead_ratio']:>8.2f}x "
                f"{comparison['trace_overhead_percent']:>9.1f}%"
            )
    return "\n".join(lines)
