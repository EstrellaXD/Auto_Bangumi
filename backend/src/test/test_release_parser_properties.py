"""Metamorphic and invariant checks for the public release parser.

The suite intentionally avoids depending on tokenizer implementation details.
It uses a fixed pseudo-random seed and keeps the combined generated corpus below
500 cases so failures stay reproducible and the test remains cheap to run.
"""

from __future__ import annotations

import math
import random
import re
import string
from collections.abc import Iterable

from module.parser.analyser.tokenizer import (
    MediaType,
    ParsedRelease,
    ReleaseKind,
    parse_release_title,
)

SEED = 0xAB330
STRUCTURED_EPISODE_CASES = 4 * 3 * 3 * 3
STRUCTURED_MEDIA_CASES = 15 * 4
METAMORPHIC_CASES = 60
FUZZ_CASES = 220
GENERATED_CASES = (
    STRUCTURED_EPISODE_CASES + STRUCTURED_MEDIA_CASES + METAMORPHIC_CASES + FUZZ_CASES
)


def _normalized_titles(parsed: ParsedRelease) -> tuple[str, ...]:
    """Compare title content without prescribing language-slot heuristics."""
    return tuple(
        sorted(
            re.sub(r"\s+", " ", title).strip().casefold()
            for title in (parsed.title_en, parsed.title_zh, parsed.title_jp)
            if title
        )
    )


def _core_identity(parsed: ParsedRelease) -> tuple[object, ...]:
    """Fields that technical adornments must not change."""
    return (
        _normalized_titles(parsed),
        parsed.group,
        parsed.season,
        parsed.episode,
        parsed.episode_end,
        parsed.episode_title,
        parsed.media_type,
        parsed.release_kind,
        parsed.version,
        parsed.year,
    )


def _title_contains(parsed: ParsedRelease, expected: str) -> bool:
    expected = re.sub(r"\s+", " ", expected).strip().casefold()
    return any(expected in title for title in _normalized_titles(parsed))


def _assert_public_invariants(raw: str, parsed: ParsedRelease | None) -> None:
    """Check only guarantees implied by the public result contract."""
    assert parsed == parse_release_title(raw), f"non-deterministic parse for {raw!r}"
    if parsed is None:
        return

    assert parsed.raw == raw
    assert isinstance(parsed.media_type, MediaType)
    assert isinstance(parsed.release_kind, ReleaseKind)
    assert parsed.primary_title is not None
    assert parsed.primary_title.strip()
    assert _normalized_titles(parsed)

    for title in (parsed.title_en, parsed.title_zh, parsed.title_jp):
        if title is not None:
            assert title == title.strip()

    for number in (parsed.episode, parsed.episode_end):
        if number is not None:
            assert isinstance(number, (int, float)) and not isinstance(number, bool)
            assert math.isfinite(float(number))
            assert number >= 0

    if parsed.episode_end is not None:
        assert parsed.episode is not None
    if parsed.season is not None:
        assert isinstance(parsed.season, int) and not isinstance(parsed.season, bool)
        assert parsed.season >= 0
    if parsed.version is not None:
        assert isinstance(parsed.version, int) and parsed.version >= 0

    assert isinstance(parsed.codecs, tuple)
    assert isinstance(parsed.audio, tuple)
    assert isinstance(parsed.tags, tuple)
    assert isinstance(parsed.evidence, tuple)


def test_generated_corpus_stays_within_budget() -> None:
    assert GENERATED_CASES == 448
    assert GENERATED_CASES <= 500


def test_technical_adornments_preserve_numbered_episode_identity() -> None:
    titles = ("Sousou no Frieren", "葬送的芙莉莲", "Fate stay night", "86")
    groups = ("LoliHouse", "字幕组", "Movie-Fan")
    episodes = ((1, "01"), (7, "07"), (12.5, "12.5"))
    adornments = (
        " [1080p WEB-DL HEVC AAC MKV]",
        " [720p BDRip AVC FLAC].mkv",
        " 【2160p BluRay x265 Dual Audio】",
    )

    seen = 0
    for title in titles:
        for group in groups:
            for expected_episode, episode_text in episodes:
                baseline_raw = f"[{group}] {title} - {episode_text}"
                baseline = parse_release_title(baseline_raw)
                assert baseline is not None, baseline_raw
                _assert_public_invariants(baseline_raw, baseline)

                for adornment in adornments:
                    raw = baseline_raw + adornment
                    parsed = parse_release_title(raw)
                    assert parsed is not None, raw
                    _assert_public_invariants(raw, parsed)
                    assert _core_identity(parsed) == _core_identity(baseline), raw
                    assert parsed.episode == expected_episode, raw
                    assert parsed.media_type is MediaType.EPISODE, raw
                    assert parsed.release_kind is ReleaseKind.SINGLE, raw
                    seen += 1

    assert seen == STRUCTURED_EPISODE_CASES


def test_structured_media_forms_survive_safe_wrapping_variants() -> None:
    forms: tuple[
        tuple[str, str, MediaType, ReleaseKind, int | float | None, int | float | None],
        ...,
    ] = (
        (
            "Meta Anime - 01",
            "Meta Anime",
            MediaType.EPISODE,
            ReleaseKind.SINGLE,
            1,
            None,
        ),
        (
            "Meta Anime - 12.5",
            "Meta Anime",
            MediaType.EPISODE,
            ReleaseKind.SINGLE,
            12.5,
            None,
        ),
        (
            "Meta Anime - 12v2",
            "Meta Anime",
            MediaType.EPISODE,
            ReleaseKind.SINGLE,
            12,
            None,
        ),
        (
            "Meta Anime S02E05",
            "Meta Anime",
            MediaType.EPISODE,
            ReleaseKind.SINGLE,
            5,
            None,
        ),
        (
            "Meta Anime [01-12]",
            "Meta Anime",
            MediaType.EPISODE,
            ReleaseKind.RANGE,
            1,
            12,
        ),
        (
            "Meta Anime Complete Batch",
            "Meta Anime",
            MediaType.EPISODE,
            ReleaseKind.BATCH,
            None,
            None,
        ),
        ("迷宫饭 全24话", "迷宫饭", MediaType.EPISODE, ReleaseKind.COLLECTION, 1, 24),
        ("Meta Anime OVA01", "Meta Anime", MediaType.OVA, ReleaseKind.SINGLE, 1, None),
        ("Meta Anime OAD02", "Meta Anime", MediaType.OAD, ReleaseKind.SINGLE, 2, None),
        (
            "Meta Anime SP03",
            "Meta Anime",
            MediaType.SPECIAL,
            ReleaseKind.SINGLE,
            3,
            None,
        ),
        (
            "劇場版 Meta Anime",
            "Meta Anime",
            MediaType.MOVIE,
            ReleaseKind.SINGLE,
            None,
            None,
        ),
        ("Meta Anime PV2", "Meta Anime", MediaType.PV, ReleaseKind.SINGLE, 2, None),
        (
            "Meta Anime NCOP",
            "Meta Anime",
            MediaType.OPENING,
            ReleaseKind.SINGLE,
            None,
            None,
        ),
        (
            "Meta Anime NCED",
            "Meta Anime",
            MediaType.ENDING,
            ReleaseKind.SINGLE,
            None,
            None,
        ),
        ("Meta Anime", "Meta Anime", MediaType.UNKNOWN, ReleaseKind.SINGLE, None, None),
    )

    wrappers = (
        lambda value: value,
        lambda value: f"[MetaGroup] {value} [1080p WEB-DL]",
        lambda value: f"【MetaGroup】 {value} 【720p BDRip AVC AAC】.mkv",
        lambda value: f"\n  [MetaGroup] {value} [HEVC][1080P]  \n",
    )

    seen = 0
    for core, title, media_type, release_kind, episode, episode_end in forms:
        for wrap in wrappers:
            raw = wrap(core)
            parsed = parse_release_title(raw)
            assert parsed is not None, raw
            _assert_public_invariants(raw, parsed)
            assert _title_contains(parsed, title), raw
            assert parsed.media_type is media_type, raw
            assert parsed.release_kind is release_kind, raw
            assert parsed.episode == episode, raw
            assert parsed.episode_end == episode_end, raw
            seen += 1

    assert seen == STRUCTURED_MEDIA_CASES


def test_whitespace_bracket_and_metadata_variants_preserve_core_identity() -> None:
    rng = random.Random(SEED)
    titles = ("Mob Psycho 100", "Dungeon Meshi", "葬送的芙莉莲", "Fate stay night")
    groups = ("Group-A", "Lilith-Raws", "喵萌奶茶屋")

    for _ in range(METAMORPHIC_CASES):
        title = rng.choice(titles)
        group = rng.choice(groups)
        season = rng.randint(1, 12)
        episode = rng.randint(1, 99)
        version = rng.randint(1, 3)
        marker = f"S{season:02d}E{episode:02d}v{version}"
        baseline_raw = f"[{group}] {title} {marker}"
        variant_raw = (
            f"\n  【{group}】 {title} {marker.lower()} "
            "【WEB-DL 1080p HEVC AAC MKV】.mkv  \n"
        )

        baseline = parse_release_title(baseline_raw)
        variant = parse_release_title(variant_raw)
        assert baseline is not None, baseline_raw
        assert variant is not None, variant_raw
        _assert_public_invariants(baseline_raw, baseline)
        _assert_public_invariants(variant_raw, variant)
        assert _core_identity(variant) == _core_identity(baseline), variant_raw


def _random_inputs(rng: random.Random, count: int) -> Iterable[str]:
    atoms = (
        "Anime",
        "Title",
        "葬送的芙莉莲",
        "アニメ",
        "OVA",
        "OAD02",
        "SP",
        "PV2",
        "NCOP",
        "NCED",
        "S02E05",
        "Season 3",
        "01-12",
        "12.5",
        "Complete Batch",
        "劇場版",
        "WEB-DL",
        "BDRip",
        "1080p",
        "HEVC",
        "AAC",
        "MKV",
        "[",
        "]",
        "(",
        ")",
        "【",
        "】",
    )
    separators = ("", " ", "  ", " - ", "_", "/", ".", "\n")
    alphabet = string.ascii_letters + string.digits + " []()_-./~中日語話季\n"

    for index in range(count):
        if index % 2:
            parts = [rng.choice(atoms) for _ in range(rng.randint(0, 12))]
            yield rng.choice(separators).join(parts)
        else:
            yield "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 120)))


def test_seeded_fuzz_inputs_are_total_and_deterministic() -> None:
    rng = random.Random(SEED)
    corpus = list(_random_inputs(rng, FUZZ_CASES))
    assert len(corpus) == FUZZ_CASES

    for raw in corpus:
        _assert_public_invariants(raw, parse_release_title(raw))
