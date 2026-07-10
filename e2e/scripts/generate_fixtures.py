#!/usr/bin/env python3
"""Generate deterministic binary fixtures for the hermetic E2E stack."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures"
MEDIA_PATH = Path("files/tiny-media.mkv")
TORRENT_PATH = Path("torrents/tiny-media.torrent")
CHECKSUM_PATH = Path("checksums.json")
GENERATED_PATHS = (MEDIA_PATH, TORRENT_PATH)

MEDIA_NAME = "Tiny Show - 01 [E2E].mkv"
WEB_SEED = "http://mock-upstream:18888/files/tiny-media.mkv"
PIECE_LENGTH = 16 * 1024


def bencode(value: bytes | str | int | list | tuple | dict) -> bytes:
    """Encode the small bencode subset used by the single-file torrent."""
    if isinstance(value, bytes):
        return str(len(value)).encode() + b":" + value
    if isinstance(value, str):
        return bencode(value.encode())
    if isinstance(value, int):
        return b"i" + str(value).encode() + b"e"
    if isinstance(value, (list, tuple)):
        return b"l" + b"".join(bencode(item) for item in value) + b"e"
    if isinstance(value, dict):
        items: list[tuple[bytes, object]] = []
        for key, item in value.items():
            encoded_key = key if isinstance(key, bytes) else str(key).encode()
            items.append((encoded_key, item))
        return (
            b"d"
            + b"".join(bencode(key) + bencode(item) for key, item in sorted(items))
            + b"e"
        )
    raise TypeError(f"Unsupported bencode value: {type(value)!r}")


def build_media() -> bytes:
    """Return a stable 64 KiB payload without random or timestamp input."""
    return bytes(range(256)) * 256


def build_torrent(media: bytes) -> bytes:
    """Return trackerless single-file metainfo backed by the local web seed."""
    pieces = b"".join(
        hashlib.sha1(media[offset : offset + PIECE_LENGTH]).digest()
        for offset in range(0, len(media), PIECE_LENGTH)
    )
    return bencode(
        {
            b"created by": b"AutoBangumi hermetic E2E",
            b"creation date": 0,
            b"info": {
                b"length": len(media),
                b"name": MEDIA_NAME,
                b"piece length": PIECE_LENGTH,
                b"pieces": pieces,
            },
            b"url-list": WEB_SEED,
        }
    )


def generated_content() -> dict[Path, bytes]:
    media = build_media()
    return {MEDIA_PATH: media, TORRENT_PATH: build_torrent(media)}


def _checksum_content(content: dict[Path, bytes]) -> bytes:
    checksums = {
        str(path): hashlib.sha256(data).hexdigest() for path, data in content.items()
    }
    return (json.dumps(checksums, indent=2, sort_keys=True) + "\n").encode()


def write_fixtures(root: Path = FIXTURE_ROOT) -> None:
    content = generated_content()
    for relative_path, data in content.items():
        destination = root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    (root / CHECKSUM_PATH).write_bytes(_checksum_content(content))


def check_fixtures(root: Path = FIXTURE_ROOT) -> list[str]:
    content = generated_content()
    expected = {**content, CHECKSUM_PATH: _checksum_content(content)}
    mismatches: list[str] = []
    for relative_path, data in expected.items():
        destination = root / relative_path
        if not destination.exists():
            mismatches.append(f"missing: {relative_path}")
        elif destination.read_bytes() != data:
            mismatches.append(f"out of date: {relative_path}")
    return mismatches


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=FIXTURE_ROOT)
    args = parser.parse_args()

    if args.check:
        mismatches = check_fixtures(args.output)
        if mismatches:
            print("\n".join(mismatches))
            return 1
        print("E2E binary fixtures are deterministic and up to date.")
        return 0

    write_fixtures(args.output)
    print(f"Wrote deterministic E2E fixtures to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
