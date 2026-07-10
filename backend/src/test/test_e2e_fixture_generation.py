"""Contract tests for deterministic hermetic E2E fixture generation."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = REPO_ROOT / "e2e" / "fixtures"
GENERATOR_PATH = REPO_ROOT / "e2e" / "scripts" / "generate_fixtures.py"


def _load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "e2e_generate_fixtures", GENERATOR_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bdecode(data: bytes, index: int = 0):
    token = data[index : index + 1]
    if token == b"i":
        end = data.index(b"e", index)
        return int(data[index + 1 : end]), end + 1
    if token == b"l":
        result = []
        index += 1
        while data[index : index + 1] != b"e":
            value, index = _bdecode(data, index)
            result.append(value)
        return result, index + 1
    if token == b"d":
        result = {}
        index += 1
        while data[index : index + 1] != b"e":
            key, index = _bdecode(data, index)
            value, index = _bdecode(data, index)
            result[key] = value
        return result, index + 1
    colon = data.index(b":", index)
    length = int(data[index:colon])
    start = colon + 1
    end = start + length
    return data[start:end], end


def test_generated_binary_fixtures_match_committed_bytes(tmp_path: Path):
    generator = _load_generator()
    generated_root = tmp_path / "fixtures"

    generator.write_fixtures(generated_root)

    for relative_path in generator.GENERATED_PATHS:
        assert (generated_root / relative_path).read_bytes() == (
            FIXTURE_ROOT / relative_path
        ).read_bytes()

    checksums = json.loads((FIXTURE_ROOT / "checksums.json").read_text())
    assert checksums == {
        str(path): hashlib.sha256((FIXTURE_ROOT / path).read_bytes()).hexdigest()
        for path in generator.GENERATED_PATHS
    }


def test_torrent_contains_only_local_web_seed_and_valid_piece_hashes():
    torrent, end = _bdecode(
        (FIXTURE_ROOT / "torrents" / "tiny-media.torrent").read_bytes()
    )
    media = (FIXTURE_ROOT / "files" / "tiny-media.mkv").read_bytes()

    assert end == len((FIXTURE_ROOT / "torrents" / "tiny-media.torrent").read_bytes())
    assert torrent[b"url-list"] == (b"http://mock-upstream:18888/files/tiny-media.mkv")
    info = torrent[b"info"]
    assert info[b"name"] == b"Tiny Show - 01 [E2E].mkv"
    assert info[b"length"] == len(media) == 64 * 1024
    assert info[b"piece length"] == 16 * 1024
    assert info[b"pieces"] == b"".join(
        hashlib.sha1(media[offset : offset + info[b"piece length"]]).digest()
        for offset in range(0, len(media), info[b"piece length"])
    )


def test_text_fixtures_reference_only_hermetic_hosts():
    allowed_hosts = {"mock-upstream", "127.0.0.1", "localhost"}
    urls: list[str] = []
    for pattern in ("*.xml", "*.json", "*.html"):
        for path in FIXTURE_ROOT.rglob(pattern):
            urls.extend(re.findall(r"https?://[^\s\"'<>]+", path.read_text()))

    assert urls
    assert {urlparse(url).hostname for url in urls} <= allowed_hosts
