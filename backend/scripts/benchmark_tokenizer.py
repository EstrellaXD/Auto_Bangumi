#!/usr/bin/env python3
"""Benchmark the generic release-title tokenizer.

Run from ``backend`` with::

    uv run python scripts/benchmark_tokenizer.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_ROOT.parent
_SRC_ROOT = _BACKEND_ROOT / "src"
sys.path.insert(0, str(_SRC_ROOT))

from module.parser.analyser.tokenizer.benchmark import (  # noqa: E402
    load_corpus,
    render_text,
    run_benchmark,
)

_DEFAULT_CORPUS = _SRC_ROOT / "test" / "fixtures" / "release_title_golden.json"


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark plain and traced parsing on the stable golden corpus. "
            "Timing never changes the exit status or acts as a CI threshold."
        )
    )
    parser.add_argument("--mode", choices=("plain", "trace", "both"), default="both")
    parser.add_argument("--suite", choices=("real", "stress", "all"), default="real")
    parser.add_argument("--corpus", type=Path, default=_DEFAULT_CORPUS)
    parser.add_argument("--warmup-rounds", type=_non_negative_int, default=20)
    parser.add_argument("--samples", type=_positive_int, default=7)
    parser.add_argument("--min-sample-ms", type=_positive_float, default=250.0)
    parser.add_argument(
        "--loops",
        type=_positive_int,
        help="fixed batch loop count; by default it is calibrated per group",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", type=Path, help="write the report to this path")
    parser.add_argument(
        "--quiet", action="store_true", help="hide calibration progress on stderr"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    modes = ("plain", "trace") if args.mode == "both" else (args.mode,)
    progress = None if args.quiet else lambda message: print(message, file=sys.stderr)

    try:
        corpus = load_corpus(args.corpus)
        report = run_benchmark(
            corpus,
            repo_root=_REPO_ROOT,
            modes=modes,
            suite=args.suite,
            warmup_rounds=args.warmup_rounds,
            samples=args.samples,
            target_ns=int(args.min_sample_ms * 1_000_000),
            loops=args.loops,
            progress=progress,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"benchmark failed: {exc}", file=sys.stderr)
        return 2

    output = (
        json.dumps(report, ensure_ascii=False, indent=2)
        if args.format == "json"
        else render_text(report)
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
        print(f"wrote benchmark report to {args.output}", file=sys.stderr)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
