#!/usr/bin/env python3
"""Collect and redact diagnostics from a running hermetic E2E stack."""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterable, Mapping, Sequence

REDACTED = "[REDACTED]"
_AUTH_RE = re.compile(r"(?i)\bAuthorization\b\s*[:=]\s*(?:Bearer\s+)?[^\s,;]+")
_SENSITIVE_RE = re.compile(
    r"(?i)\b(password|passwd|secret|token|cookie|sid)\b"
    r"(\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)


def redact_text(text: str, secrets: Iterable[str] = ()) -> str:
    redacted = text
    for secret in sorted({value for value in secrets if value}, key=len, reverse=True):
        redacted = redacted.replace(secret, REDACTED)
    redacted = _AUTH_RE.sub(f"Authorization: {REDACTED}", redacted)
    redacted = _SENSITIVE_RE.sub(
        lambda match: f"{match.group(1)}{match.group(2)}{REDACTED}", redacted
    )
    return redacted


def _write_redacted(path: Path, text: str, secrets: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(redact_text(text, secrets), encoding="utf-8")


def _capture(
    command: Sequence[str],
    path: Path,
    *,
    environment: Mapping[str, str] | None,
    secrets: Iterable[str],
) -> None:
    try:
        result = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
            env=dict(environment) if environment is not None else None,
        )
        output = (
            f"$ {' '.join(command)}\nexit={result.returncode}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    except Exception as exc:  # Diagnostics must never hide the test failure.
        output = f"$ {' '.join(command)}\ncollection failed: {exc!r}\n"
    _write_redacted(path, output, secrets)


def _fetch_json(url: str, *, opener=None) -> str:
    client = opener or urllib.request
    with client.urlopen(url, timeout=5) as response:
        payload = response.read().decode("utf-8", errors="replace")
    try:
        return json.dumps(json.loads(payload), indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        return payload


def _collect_admin(
    name: str,
    base_url: str,
    artifact_dir: Path,
    secrets: Iterable[str],
) -> None:
    for endpoint in ("requests", "state"):
        try:
            payload = _fetch_json(f"{base_url.rstrip('/')}/__admin/{endpoint}")
        except Exception as exc:
            payload = f"request failed: {exc!r}\n"
        _write_redacted(
            artifact_dir / f"{name}-{endpoint}.json",
            payload,
            secrets,
        )


def _collect_qbittorrent(
    base_url: str,
    artifact_dir: Path,
    secrets: Iterable[str],
    *,
    username: str = "admin",
    password: str = "adminadmin",
) -> None:
    cookies = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
    login = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/v2/auth/login",
        data=urllib.parse.urlencode(
            {"username": username, "password": password}
        ).encode("utf-8"),
    )
    try:
        with opener.open(login, timeout=5) as response:
            response.read()
        payload = _fetch_json(
            f"{base_url.rstrip('/')}/api/v2/torrents/info", opener=opener
        )
    except Exception as exc:
        payload = f"qBittorrent state request failed: {exc!r}\n"
    _write_redacted(artifact_dir / "qbittorrent-state.json", payload, secrets)


def collect_artifacts(
    *,
    compose_command: Sequence[str],
    artifact_dir: Path,
    data_dir: Path,
    log_file: Path,
    admin_urls: Mapping[str, str] | None = None,
    qb_url: str | None = None,
    environment: Mapping[str, str] | None = None,
    secrets: Iterable[str] = (),
) -> Path:
    """Best-effort collection; failures are written into the bundle."""
    artifact_dir.mkdir(parents=True, exist_ok=True)
    all_secrets = tuple(secrets) + ("adminadmin",)
    _capture(
        [*compose_command, "ps", "--all"],
        artifact_dir / "compose-ps.txt",
        environment=environment,
        secrets=all_secrets,
    )
    _capture(
        [*compose_command, "logs", "--no-color", "--timestamps"],
        artifact_dir / "compose-logs.txt",
        environment=environment,
        secrets=all_secrets,
    )

    for name, base_url in (admin_urls or {}).items():
        _collect_admin(name, base_url, artifact_dir, all_secrets)
    if qb_url:
        _collect_qbittorrent(qb_url, artifact_dir, all_secrets)

    if log_file.is_file():
        _write_redacted(
            artifact_dir / "backend-log.txt",
            log_file.read_text(encoding="utf-8", errors="replace"),
            all_secrets,
        )
    for name in ("data.db", "data.db-wal", "data.db-shm"):
        source = data_dir / name
        if source.is_file():
            shutil.copy2(source, artifact_dir / name)
    return artifact_dir


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", required=True, type=Path)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--log-file", required=True, type=Path)
    parser.add_argument("compose", nargs=argparse.REMAINDER)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.compose:
        raise SystemExit("compose command prefix is required after --")
    command = args.compose[1:] if args.compose[0] == "--" else args.compose
    collect_artifacts(
        compose_command=command,
        artifact_dir=args.artifact_dir,
        data_dir=args.data_dir,
        log_file=args.log_file,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
