#!/usr/bin/env python3
"""Classify a GitHub Actions trigger without deriving versions from PR data."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

STABLE_TAG = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
PRERELEASE_TAG = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+-(?:alpha|beta)\.[0-9]+$")


class ReleaseClassificationError(ValueError):
    """Raised when a release-shaped trigger is unsafe or unverifiable."""


def classify_release(
    *,
    event_name: str,
    ref_type: str,
    ref_name: str,
    pr_head: str = "",
    pr_title: str = "",
    stable_tag_on_main: bool | None = None,
) -> dict[str, str]:
    """Return the four outputs consumed by the release workflow.

    ``pr_title`` is accepted so callers can pass complete event metadata, but
    is deliberately never used as a version source.
    """
    del pr_title
    result = {
        "release": "0",
        "dev": "0",
        "build_test": "0",
        "version": "Test",
    }

    if ref_type == "tag" and STABLE_TAG.fullmatch(ref_name):
        if stable_tag_on_main is None:
            raise ReleaseClassificationError(
                f"Stable tag {ref_name} ancestry was not verified"
            )
        if not stable_tag_on_main:
            raise ReleaseClassificationError(
                f"Stable tag {ref_name} does not point to a commit on main; "
                "refusing to release"
            )
        return {
            **result,
            "release": "1",
            "version": ref_name,
        }

    if ref_type == "tag" and PRERELEASE_TAG.fullmatch(ref_name):
        return {
            **result,
            "release": "1",
            "dev": "1",
            "version": ref_name,
        }

    if event_name == "pull_request" and "dev" in pr_head:
        result["build_test"] = "1"

    return result


def _is_main_ancestor(sha: str, main_ref: str) -> bool:
    if not sha:
        raise ReleaseClassificationError(
            "GITHUB_SHA is required to verify a stable release tag"
        )
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", sha, main_ref],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    detail = completed.stderr.strip() or "git merge-base failed"
    raise ReleaseClassificationError(
        f"Unable to verify stable tag ancestry against {main_ref}: {detail}"
    )


def _write_outputs(outputs: dict[str, str], destination: str) -> None:
    payload = "".join(f"{key}={value}\n" for key, value in outputs.items())
    if destination:
        with Path(destination).open("a", encoding="utf-8") as output_file:
            output_file.write(payload)
    else:
        sys.stdout.write(payload)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-name", default=os.environ.get("EVENT_NAME", ""))
    parser.add_argument("--ref-type", default=os.environ.get("REF_TYPE", ""))
    parser.add_argument("--ref-name", default=os.environ.get("REF_NAME", ""))
    parser.add_argument("--pr-head", default=os.environ.get("HEAD_REF", ""))
    parser.add_argument("--pr-title", default=os.environ.get("PR_TITLE", ""))
    parser.add_argument("--sha", default=os.environ.get("GITHUB_SHA", ""))
    parser.add_argument("--main-ref", default="origin/main")
    parser.add_argument(
        "--output",
        default=os.environ.get("GITHUB_OUTPUT", ""),
        help="GitHub Actions output file; stdout when omitted",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        stable_tag_on_main = None
        if args.ref_type == "tag" and STABLE_TAG.fullmatch(args.ref_name):
            stable_tag_on_main = _is_main_ancestor(args.sha, args.main_ref)
        outputs = classify_release(
            event_name=args.event_name,
            ref_type=args.ref_type,
            ref_name=args.ref_name,
            pr_head=args.pr_head,
            pr_title=args.pr_title,
            stable_tag_on_main=stable_tag_on_main,
        )
        _write_outputs(outputs, args.output)
    except ReleaseClassificationError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
