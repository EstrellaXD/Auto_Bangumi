#!/usr/bin/env python3
"""Statically reject non-hermetic or collision-prone E2E source patterns."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import urlsplit

_URL_RE = re.compile(r"https?://[^\s\"'<>]+")
_FIXED_PORT_RE = re.compile(r"127\.0\.0\.1:(?!0:)\d+:\d+")
_BLIND_SLEEP_RE = re.compile(r"\b(?:time\.)?sleep\(\s*\d+(?:\.\d+)?\s*\)")
_ALLOWED_HOSTS = {
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "localhost",
    "mock-upstream",
    "fake-qb",
    "qbittorrent",
}


@dataclass(frozen=True)
class AuditFinding:
    path: Path
    line: int
    message: str


def _source_files(root: Path) -> Iterable[Path]:
    e2e_root = root / "e2e"
    if e2e_root.exists():
        for path in e2e_root.rglob("*"):
            if path.is_file() and (
                path.name == "Dockerfile"
                or path.suffix in {".py", ".yml", ".yaml", ".ts"}
            ):
                if path.name == "audit_sources.py":
                    continue
                yield path
    playwright = root / "webui/playwright.config.ts"
    if playwright.is_file():
        yield playwright


def _add(
    findings: list[AuditFinding],
    path: Path,
    line: int,
    message: str,
) -> None:
    findings.append(AuditFinding(path=path, line=line, message=message))


def _audit_line(
    root: Path,
    path: Path,
    line_number: int,
    line: str,
    findings: list[AuditFinding],
) -> None:
    relative = path.relative_to(root)
    if "container_name" in line:
        _add(findings, relative, line_number, "container_name is forbidden")
    if ":latest" in line:
        _add(findings, relative, line_number, "floating image tag is forbidden")
    if _FIXED_PORT_RE.search(line):
        _add(findings, relative, line_number, "fixed host port is forbidden")
    if path.name not in {"stack.py", "poll.py"} and _BLIND_SLEEP_RE.search(line):
        _add(findings, relative, line_number, "blind sleep is forbidden")
    if path.name == "playwright.config.ts":
        retry = re.search(r"\bretries\s*:\s*(\d+)", line)
        if retry and int(retry.group(1)) != 0:
            _add(findings, relative, line_number, "Playwright retries must be zero")
    for raw_url in _URL_RE.findall(line):
        try:
            hostname = urlsplit(raw_url.rstrip("),];")).hostname
        except ValueError:
            if "{" in raw_url:  # A local f-string URL is checked after expansion.
                continue
            _add(findings, relative, line_number, "malformed URL in E2E source")
            continue
        if hostname and hostname not in _ALLOWED_HOSTS:
            _add(
                findings,
                relative,
                line_number,
                f"public upstream host is forbidden: {hostname}",
            )


def _audit_image_references(
    root: Path,
    path: Path,
    lines: list[str],
    findings: list[AuditFinding],
) -> None:
    relative = path.relative_to(root)
    if path.name == "Dockerfile":
        for line_number, line in enumerate(lines, 1):
            match = re.match(r"\s*FROM\s+(\S+)", line, re.I)
            if match and "@sha256:" not in match.group(1):
                _add(
                    findings,
                    relative,
                    line_number,
                    "external Dockerfile base image must use an immutable digest",
                )
    if path.suffix in {".yml", ".yaml"}:
        for line_number, line in enumerate(lines, 1):
            match = re.match(r"\s*image:\s*([^\s#]+)", line)
            if not match:
                continue
            image = match.group(1).strip("\"'")
            if image.startswith("${"):
                continue
            if "/" in image and "@sha256:" not in image:
                _add(
                    findings,
                    relative,
                    line_number,
                    "external Compose image must use an immutable digest",
                )


def audit_repository(root: Path) -> list[AuditFinding]:
    root = root.resolve()
    findings: list[AuditFinding] = []
    for path in sorted(set(_source_files(root))):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        lines = text.splitlines()
        for line_number, line in enumerate(lines, 1):
            _audit_line(root, path, line_number, line, findings)
        _audit_image_references(root, path, lines, findings)
    return findings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    findings = audit_repository(args.root)
    for finding in findings:
        print(f"{finding.path}:{finding.line}: {finding.message}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
