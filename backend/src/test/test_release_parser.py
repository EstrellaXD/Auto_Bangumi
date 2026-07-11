"""Contract tests for the generic release-title parser.

The generic API intentionally keeps an absent episode as ``None``.  Legacy
``raw_parser`` compatibility (including its zero sentinel) is covered by the
older parser tests and is not part of this suite.
"""

from __future__ import annotations

from typing import Any

import pytest

from module.parser.analyser.raw_parser import raw_parser
from module.parser.analyser.tokenizer import parse_release_title
from module.parser.analyser.tokenizer.result import MediaType, ReleaseKind

REQUIRED_FIELDS = (
    "raw",
    "title_en",
    "title_zh",
    "title_jp",
    "group",
    "season",
    "episode",
    "episode_end",
    "episode_title",
    "media_type",
    "release_kind",
    "resolution",
    "source",
    "subtitle",
    "codecs",
    "audio",
    "container",
    "version",
)


def _title_text(parsed: Any) -> str:
    """Join title slots so tests do not prescribe a language heuristic."""
    return " | ".join(
        title for title in (parsed.title_en, parsed.title_zh, parsed.title_jp) if title
    )


def test_generic_result_contract_and_standard_episode() -> None:
    raw = (
        "[LoliHouse] 葬送的芙莉莲 / Sousou no Frieren - 03 "
        "[WebRip 1080p HEVC-10bit AAC][简繁内封字幕][MKV]"
    )

    parsed = parse_release_title(raw)

    assert parsed is not None
    for field in REQUIRED_FIELDS:
        assert hasattr(parsed, field), field
    assert parsed.raw == raw
    assert parsed.group == "LoliHouse"
    assert parsed.episode == 3
    assert parsed.episode_end is None
    assert parsed.resolution is not None
    assert parsed.resolution.lower() == "1080p"
    assert "葬送的芙莉莲" in _title_text(parsed)
    assert "Sousou no Frieren" in _title_text(parsed)
    assert parsed.media_type is MediaType.EPISODE
    assert parsed.release_kind is ReleaseKind.SINGLE


@pytest.mark.parametrize(
    ("raw", "season", "episode", "version"),
    [
        ("[Group] Anime Title S02E05 [WEB-DL 1080p]", 2, 5, None),
        ("[Group] Anime Title Season 2 - 01 [1080p]", 2, 1, None),
        ("[Group] Anime Title - 12.5 [1080p]", None, 12.5, None),
        ("[Group] Anime Title - 12v2 [1080p]", None, 12, 2),
    ],
)
def test_numbered_release_forms(
    raw: str,
    season: int | None,
    episode: int | float,
    version: int | None,
) -> None:
    parsed = parse_release_title(raw)

    assert parsed is not None
    assert "Anime Title" in _title_text(parsed)
    assert parsed.episode == episode
    assert parsed.episode_end is None
    assert parsed.version == version
    if season is not None:
        assert parsed.season == season
    assert parsed.media_type is MediaType.EPISODE
    assert parsed.release_kind is ReleaseKind.SINGLE


@pytest.mark.parametrize(
    "raw",
    [
        "[Group] Anime Title [01-12] [BDRip 1080p]",
        "[Group] Anime Title [E01-E12] [BDRip 1080p]",
    ],
)
def test_episode_range_is_a_range_release(raw: str) -> None:
    parsed = parse_release_title(raw)

    assert parsed is not None
    assert "Anime Title" in _title_text(parsed)
    assert parsed.episode == 1
    assert parsed.episode_end == 12
    assert parsed.media_type is MediaType.EPISODE
    assert parsed.release_kind is ReleaseKind.RANGE


def test_complete_batch_without_episode_number() -> None:
    parsed = parse_release_title(
        "[VCB-Studio] Violet Evergarden Complete Batch [BDRip 1080p]"
    )

    assert parsed is not None
    assert "Violet Evergarden" in _title_text(parsed)
    assert parsed.episode is None
    assert parsed.episode_end is None
    assert parsed.media_type is MediaType.EPISODE
    assert parsed.release_kind is ReleaseKind.BATCH


@pytest.mark.parametrize(
    ("raw", "title_fragment"),
    [
        ("[Group] 葬送的芙莉莲合集 [BDRip 1080p]", "葬送的芙莉莲"),
        ("[Group] 葬送的芙莉莲全集 [BDRip 1080p]", "葬送的芙莉莲"),
        ("[Group] 进击的巨人总集篇 [BDRip 1080p]", "进击的巨人"),
        ("[Group] Anime Title 特典 [BDRip 1080p]", "Anime Title"),
    ],
)
def test_chinese_collection_without_episode(raw: str, title_fragment: str) -> None:
    parsed = parse_release_title(raw)

    assert parsed is not None
    assert title_fragment in _title_text(parsed)
    assert parsed.episode is None
    assert parsed.episode_end is None
    assert parsed.release_kind is ReleaseKind.COLLECTION


def test_movie_collection_keeps_both_dimensions() -> None:
    parsed = parse_release_title("[Group] 剧场版合集 - 进击的巨人 [1080p]")

    assert parsed is not None
    assert parsed.title_zh == "进击的巨人"
    assert parsed.media_type is MediaType.MOVIE
    assert parsed.release_kind is ReleaseKind.COLLECTION


@pytest.mark.parametrize(
    ("raw", "media_type", "episode"),
    [
        ("[Group] Anime Title OVA01 [BDRip 1080p]", MediaType.OVA, 1),
        ("[Group] Anime Title OAD 02 [BDRip 1080p]", MediaType.OAD, 2),
        ("[Group] Anime Title SP03 [BDRip 1080p]", MediaType.SPECIAL, 3),
    ],
)
def test_numbered_special_media(raw: str, media_type: MediaType, episode: int) -> None:
    parsed = parse_release_title(raw)

    assert parsed is not None
    assert "Anime Title" in _title_text(parsed)
    assert parsed.episode == episode
    assert parsed.media_type is media_type
    assert parsed.release_kind is ReleaseKind.SINGLE


@pytest.mark.parametrize(
    ("raw", "title_fragment"),
    [
        (
            "[VCB-Studio]电影版哆啦A梦：大雄的地球交响乐[BDRip 1080p]",
            "哆啦A梦",
        ),
        (
            "[SubGroup]劇場版SPY×FAMILY CODE: White[WEB-DL 1080p]",
            "SPY×FAMILY",
        ),
    ],
)
def test_attached_movie_marker_preserves_title(raw: str, title_fragment: str) -> None:
    parsed = parse_release_title(raw)

    assert parsed is not None
    assert title_fragment in _title_text(parsed)
    assert parsed.episode is None
    assert parsed.media_type is MediaType.MOVIE
    assert parsed.release_kind is ReleaseKind.SINGLE


@pytest.mark.parametrize(
    ("raw", "media_type", "episode"),
    [
        ("[Official] Anime Title PV2 [1080p]", MediaType.PV, 2),
        (
            "[VCB-Studio] Anime Title NCOP [BDRip 1080p]",
            MediaType.OPENING,
            None,
        ),
        (
            "[VCB-Studio] Anime Title NCED [BDRip 1080p]",
            MediaType.ENDING,
            None,
        ),
    ],
)
def test_non_episode_video_kinds(
    raw: str, media_type: MediaType, episode: int | None
) -> None:
    parsed = parse_release_title(raw)

    assert parsed is not None
    assert "Anime Title" in _title_text(parsed)
    assert parsed.episode == episode
    assert parsed.media_type is media_type
    assert parsed.release_kind is ReleaseKind.SINGLE


@pytest.mark.parametrize(
    ("raw", "title_fragment"),
    [
        ("[LoliHouse] Sousou no Frieren [WEB-DL 1080p]", "Sousou no Frieren"),
        ("[VCB-Studio] Fate/stay night [BDRip 1080p]", "Fate/stay night"),
    ],
)
def test_title_only_release_is_valid(raw: str, title_fragment: str) -> None:
    parsed = parse_release_title(raw)

    assert parsed is not None
    assert title_fragment in _title_text(parsed)
    assert parsed.episode is None
    assert parsed.episode_end is None
    assert parsed.media_type is MediaType.UNKNOWN
    assert parsed.release_kind is ReleaseKind.SINGLE


def test_year_is_not_an_episode_number() -> None:
    parsed = parse_release_title("[VCB-Studio] Kimi no Na wa. (2016) [BDRip 1080p]")

    assert parsed is not None
    assert "Kimi no Na wa." in _title_text(parsed)
    assert parsed.episode is None


def test_only_technical_tags_is_not_a_release() -> None:
    assert parse_release_title("[1080p][HEVC][AAC][MKV]") is None


def test_movie_word_in_group_does_not_mark_episode_as_movie() -> None:
    parsed = parse_release_title("[Movie-Fan] Ordinary Anime - 01 [WEB-DL 1080p]")

    assert parsed is not None
    assert parsed.group == "Movie-Fan"
    assert parsed.episode == 1
    assert parsed.media_type is MediaType.EPISODE


def test_movie_word_in_regular_series_title_does_not_override_episode() -> None:
    parsed = parse_release_title(
        "[SubGroup] The Movie Star Next Door - 03 [WEB-DL 1080p]"
    )

    assert parsed is not None
    assert "Movie Star" in _title_text(parsed)
    assert parsed.episode == 3
    assert parsed.media_type is MediaType.EPISODE
    assert parsed.release_kind is ReleaseKind.SINGLE


def test_fraction_in_title_is_not_an_episode_range() -> None:
    parsed = parse_release_title("[SubGroup] Ranma 1/2 - 03 [WEB-DL 1080p]")

    assert parsed is not None
    assert "Ranma 1/2" in _title_text(parsed)
    assert parsed.episode == 3
    assert parsed.episode_end is None
    assert parsed.release_kind is ReleaseKind.SINGLE


@pytest.mark.parametrize(
    ("raw", "media_type", "season", "episode", "episode_end"),
    [
        ("[MOVIE] Anime Title [1080p]", MediaType.MOVIE, None, None, None),
        ("[劇場版] Anime Title [1080p]", MediaType.MOVIE, None, None, None),
        ("[S02E05] Anime Title [1080p]", MediaType.EPISODE, 2, 5, None),
        ("[Season 2] Anime Title - 01 [1080p]", MediaType.EPISODE, 2, 1, None),
        ("[E01-E12] Anime Title [1080p]", MediaType.EPISODE, None, 1, 12),
    ],
)
def test_leading_metadata_is_not_a_group(
    raw: str,
    media_type: MediaType,
    season: int | None,
    episode: int | None,
    episode_end: int | None,
) -> None:
    parsed = parse_release_title(raw)

    assert parsed is not None
    assert parsed.group is None
    assert "Anime Title" in _title_text(parsed)
    assert parsed.media_type is media_type
    assert parsed.season == season
    assert parsed.episode == episode
    assert parsed.episode_end == episode_end


def test_compound_technical_prefix_is_not_a_group() -> None:
    parsed = parse_release_title("[BDRip 1080p] Anime Title - 01")

    assert parsed is not None
    assert parsed.group is None
    assert parsed.source == "BDRip"
    assert parsed.resolution == "1080p"
    assert parsed.episode == 1


@pytest.mark.parametrize(
    ("raw", "media_type"),
    [
        ("[Group] 某作品OVA [1080p]", MediaType.OVA),
        ("[Group] 某作品番外篇 [1080p]", MediaType.SPECIAL),
        ("[Group] 某作品特别篇 [1080p]", MediaType.SPECIAL),
    ],
)
def test_attached_special_markers_preserve_title(
    raw: str, media_type: MediaType
) -> None:
    parsed = parse_release_title(raw)

    assert parsed is not None
    assert parsed.title_zh == "某作品"
    assert parsed.media_type is media_type


def test_numbered_complete_collection() -> None:
    parsed = parse_release_title("[Group] 迷宫饭 全24话 [1080p]")

    assert parsed is not None
    assert parsed.title_zh == "迷宫饭"
    assert parsed.episode == 1
    assert parsed.episode_end == 24
    assert parsed.release_kind is ReleaseKind.COLLECTION


def test_provider_technical_labels_do_not_pollute_title() -> None:
    parsed = parse_release_title(
        "[EMBER] Frieren - 12.5 [BDRip 1080p AVC 8bit Dual Audio Multiple Subtitle MKV]"
    )

    assert parsed is not None
    assert parsed.title_en == "Frieren"
    assert parsed.episode == 12.5
    assert "8bit" in parsed.codecs
    assert "Dual Audio" in parsed.audio
    assert parsed.subtitle == "Multiple Subtitle"


def test_plex_episode_title_is_separate_from_series_title() -> None:
    parsed = parse_release_title(
        "Mob Psycho 100 - S03E05 - Divine Tree 2 ~Peace~ [1080p]"
    )

    assert parsed is not None
    assert parsed.title_en == "Mob Psycho 100"
    assert parsed.episode_title == "Divine Tree 2 ~Peace~"
    assert parsed.season == 3
    assert parsed.episode == 5


def test_inline_year_is_metadata() -> None:
    parsed = parse_release_title("The Boy and the Heron 2023 1080p BluRay")

    assert parsed is not None
    assert parsed.title_en == "The Boy and the Heron"
    assert parsed.year == 2023


def test_pv_prefix_in_real_title_is_not_a_marker() -> None:
    parsed = parse_release_title("[Group] PV=nRT - 01 [1080p]")

    assert parsed is not None
    assert parsed.title_en == "PV=nRT"
    assert parsed.media_type is MediaType.EPISODE


@pytest.mark.parametrize(
    ("raw", "title"),
    [
        ("[Group] The Movie Star Next Door [1080p]", "The Movie Star Next Door"),
        ("[Group] Special A [1080p]", "Special A"),
    ],
)
def test_marker_words_inside_title_only_release_are_preserved(
    raw: str, title: str
) -> None:
    parsed = parse_release_title(raw)

    assert parsed is not None
    assert parsed.title_en == title
    assert parsed.media_type is MediaType.UNKNOWN


@pytest.mark.parametrize(
    ("raw", "title"),
    [
        ("[Group] 劇場版 呪術廻戦 0 [1080p]", "呪術廻戦 0"),
        ("[Group] Gekijouban Naruto 3 [1080p]", "Naruto 3"),
    ],
)
def test_movie_title_number_is_not_an_episode(raw: str, title: str) -> None:
    parsed = parse_release_title(raw)

    assert parsed is not None
    assert title in _title_text(parsed)
    assert parsed.media_type is MediaType.MOVIE
    assert parsed.episode is None


@pytest.mark.parametrize("title", ["86", "22/7"])
def test_numeric_anime_titles(title: str) -> None:
    parsed = parse_release_title(f"[Group] {title} - 01 [1080p]")

    assert parsed is not None
    assert parsed.title_en == title
    assert parsed.episode == 1


def test_ordinal_season_is_recognized() -> None:
    parsed = parse_release_title("[Group] Dandadan 2nd Season - 01 [1080p]")

    assert parsed is not None
    assert parsed.title_en == "Dandadan"
    assert parsed.season == 2
    assert parsed.episode == 1


def test_episode_mixed_with_technical_tags() -> None:
    parsed = parse_release_title("[Group] Anime Title [01 1080p HEVC]")

    assert parsed is not None
    assert parsed.title_en == "Anime Title"
    assert parsed.episode == 1
    assert parsed.resolution == "1080p"


def test_surround_audio_metadata_is_not_a_title() -> None:
    parsed = parse_release_title("[Group] Anime Title - 01 [Dual Audio][DDP5.1][1080p]")

    assert parsed is not None
    assert parsed.title_en == "Anime Title"
    assert "Dual Audio" in parsed.audio
    assert "DDP5.1" in parsed.audio


@pytest.mark.parametrize(
    "raw",
    [
        "[Group] Anime [01-12] [1080p]",
        "[Group] Anime Complete Batch [1080p]",
        "[Group] Anime PV2 [1080p]",
        "[Group] Anime NCOP [1080p]",
        "[Group] Anime - 12.5 [1080p]",
    ],
)
def test_generic_only_kinds_do_not_leak_into_legacy_parser(raw: str) -> None:
    assert parse_release_title(raw) is not None
    assert raw_parser(raw) is None
