#!/usr/bin/env python3
"""Build the native E2E image from an isolated temporary context."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, Sequence

DEFAULT_VERSION = "3.3.999-e2e.1"
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?$")


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def validate_version(version: str) -> str:
    if not _VERSION_RE.fullmatch(version):
        raise ValueError(f"E2E image version must be SemVer-compatible: {version!r}")
    return version


def tracked_backend_files(repo_root: Path) -> tuple[Path, ...]:
    """Return tracked build inputs while excluding unrelated untracked files."""
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "-z",
            "--",
            ".dockerignore",
            "Dockerfile",
            "entrypoint.sh",
            "backend",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    tracked = (
        Path(value.decode("utf-8")) for value in result.stdout.split(b"\0") if value
    )
    # `git ls-files` still reports tracked files deleted in the current
    # worktree.  Local pre-commit image verification must reflect those
    # deletions instead of trying to copy paths that intentionally no longer
    # exist.  Explicit `tracked_files` passed to `prepare_context` remain
    # strict and still surface missing required inputs.
    return tuple(path for path in tracked if (repo_root / path).is_file())


def _safe_relative(path: Path) -> Path:
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Tracked path must stay inside the repository: {path}")
    return path


def prepare_context(
    repo_root: Path,
    dist_dir: Path,
    destination: Path,
    *,
    version: str = DEFAULT_VERSION,
    tracked_files: Iterable[Path] | None = None,
) -> Path:
    """Copy tracked build inputs, WebUI dist, and version into *destination*."""
    version = validate_version(version)
    repo_root = repo_root.resolve()
    dist_dir = dist_dir.resolve()
    destination = destination.resolve()
    if not (dist_dir / "index.html").is_file():
        raise FileNotFoundError(f"Built WebUI is missing index.html: {dist_dir}")
    destination.mkdir(parents=True, exist_ok=True)

    selected = tracked_files or tracked_backend_files(repo_root)
    for relative in selected:
        relative = _safe_relative(Path(relative))
        source = repo_root / relative
        if not source.is_file():
            raise FileNotFoundError(f"Tracked build input is missing: {source}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    staged_dist = destination / "backend/src/dist"
    if staged_dist.exists():
        shutil.rmtree(staged_dist)
    shutil.copytree(dist_dir, staged_dist)

    version_module = destination / "backend/src/module/__version__.py"
    version_module.parent.mkdir(parents=True, exist_ok=True)
    version_module.write_text(f'VERSION = "{version}"\n', encoding="utf-8")
    return destination


def build_command(context: Path, *, image: str, version: str) -> list[str]:
    validate_version(version)
    if not image or any(character.isspace() for character in image):
        raise ValueError(f"Invalid Docker image name: {image!r}")
    return [
        "docker",
        "build",
        "--build-arg",
        f"VERSION={version}",
        "--tag",
        image,
        "--pull=false",
        str(context.resolve()),
    ]


def verification_command(*, image: str, version: str) -> list[str]:
    validate_version(version)
    script = (
        "import sys; "
        "from pathlib import Path; "
        "from module.__version__ import VERSION; "
        "expected=sys.argv[1]; "
        "image_version=Path('/app/IMAGE_VERSION').read_text().strip(); "
        "assert VERSION == expected == image_version, "
        "(VERSION, expected, image_version)"
    )
    return [
        "docker",
        "run",
        "--rm",
        "--entrypoint",
        "python",
        image,
        "-c",
        script,
        version,
    ]


def build_image(
    *,
    repo_root: Path,
    dist_dir: Path,
    image: str,
    version: str,
    runner=subprocess.run,
) -> None:
    with tempfile.TemporaryDirectory(prefix="ab-e2e-build-") as temporary:
        context = prepare_context(
            repo_root,
            dist_dir,
            Path(temporary) / "context",
            version=version,
        )
        runner(build_command(context, image=image, version=version), check=True)
        runner(verification_command(image=image, version=version), check=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default=DEFAULT_VERSION)
    parser.add_argument("--image", default="auto-bangumi:e2e")
    parser.add_argument("--dist", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = repository_root()
    dist = args.dist or root / "webui/dist"
    build_image(
        repo_root=root,
        dist_dir=dist,
        image=args.image,
        version=args.version,
    )
    print(f"Built and verified {args.image} at version {args.version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
