#!/usr/bin/env python3
"""Run browser and backend checks inside one fresh downloader-profile stack."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> int:
    artifact_dir = Path(os.environ["AB_E2E_ARTIFACT_DIR"])
    artifact_dir.mkdir(parents=True, exist_ok=True)
    run(
        [
            "pnpm",
            "--dir",
            "webui",
            "exec",
            "playwright",
            "test",
            "rss-download-rename.spec.ts",
            "--project=chromium-desktop",
            "--retries=0",
        ]
    )
    run(
        [
            "uv",
            "run",
            "--directory",
            "backend",
            "pytest",
            "src/test/e2e/downloader",
            "-m",
            "e2e",
            "-q",
            "--tb=long",
            f"--junitxml={artifact_dir / 'downloader-junit.xml'}",
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
