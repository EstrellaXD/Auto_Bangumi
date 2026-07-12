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

MIKAN_EXPLICIT_RANGE = (
    "才女的侍从 - EP01 ~ EP02 [简／繁] "
    "(1080p H.264 AAC SRTx2) {才女的侍从 | 才女のお世话}"
)
MIKAN_MIXED_COLLECTION = (
    "\u200b\u200b[整理搬运] 不可思议的游戏／不思议游戏／梦幻游戏／幻梦游戏 "
    "(ふしぎ游戯) (Fushigi Yugi)：TV动画+OVA+漫画+小说+音乐+其他；"
    "日语音轨; 外挂繁中字幕 (整理时间：2025.11.12)"
)
MIKAN_MIXED_ROOT = (
    "Fushigi Yugi_TV+OVA+Manga+Novel+Music+Other_" "dub jpn sub cht (2025-11-12)"
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


@pytest.mark.parametrize(
    ("raw", "episode_end", "version"),
    (
        (MIKAN_EXPLICIT_RANGE, 2, None),
        ("[Group] Anime Title E01 ～ E02 [1080p]", 2, None),
        ("[Group] Anime Title EP. 01 ～ EP. 02v2 [1080p]", 2, 2),
    ),
)
def test_both_explicit_endpoints_admit_spaced_episode_range(
    raw: str, episode_end: int, version: int | None
) -> None:
    parsed = parse_release_title(raw)

    assert parsed is not None
    assert parsed.episode == 1
    assert parsed.episode_end == episode_end
    assert parsed.version == version
    assert parsed.media_type is MediaType.EPISODE
    assert parsed.release_kind is ReleaseKind.RANGE
    assert raw_parser(raw) is None


@pytest.mark.parametrize(
    ("raw", "media_type", "season", "episode_end"),
    (
        (
            "[Group] Anime Title S02E01-E12 [1080p]",
            MediaType.EPISODE,
            2,
            12,
        ),
        (
            "[Group] Anime Title Season 2 Episodes 01-12 [1080p]",
            MediaType.EPISODE,
            2,
            12,
        ),
        (
            "[Group] Anime Title OVA01-02 [1080p]",
            MediaType.OVA,
            None,
            2,
        ),
        (
            "[Group] Anime Title OAD01-OAD03 [1080p]",
            MediaType.OAD,
            None,
            3,
        ),
    ),
)
def test_compound_range_forms_do_not_degrade_to_single_episode(
    raw: str,
    media_type: MediaType,
    season: int | None,
    episode_end: int,
) -> None:
    parsed = parse_release_title(raw)

    assert parsed is not None
    assert parsed.media_type is media_type
    assert parsed.release_kind is ReleaseKind.RANGE
    assert parsed.season == season
    assert parsed.episode == 1
    assert parsed.episode_end == episode_end
    assert raw_parser(raw) is None


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
    "raw",
    (
        MIKAN_MIXED_COLLECTION,
        "[Group] Anime Title [TV 01-12 + OVA 01-02] [BDRip 1080p]",
        "Anime Title：TV Anime+OVA+Manga+Music",
        "Anime Title：TV＋剧场版＋OVA",
        "Anime Title：[TV+OVA] [1080p]",
        "[TV+OVA; dub jpn] Anime Title [1080p]",
        "[TV+OVA_1080p] Anime Title",
        MIKAN_MIXED_ROOT,
    ),
)
def test_plus_delimited_mixed_content_manifest_is_a_collection(raw: str) -> None:
    parsed = parse_release_title(raw)

    assert parsed is not None
    assert parsed.media_type is MediaType.UNKNOWN
    assert parsed.release_kind is ReleaseKind.COLLECTION
    assert parsed.episode is None
    assert parsed.episode_end is None
    assert parsed.is_mixed_collection
    assert "mixed-content" in parsed.evidence
    title = _title_text(parsed)
    assert "TV 01-12" not in title
    assert "TV动画" not in title
    assert "+OVA" not in title
    assert raw_parser(raw) is None
    if raw == MIKAN_MIXED_COLLECTION:
        assert "整理时间" not in title
        assert "2025.11.12" in parsed.tags
    if raw == MIKAN_MIXED_ROOT:
        assert parsed.title_en == "Fushigi Yugi"
        assert parsed.subtitle is not None
        assert parsed.subtitle.casefold() == "cht"


def test_mixed_content_metadata_cleanup_preserves_real_subtitle() -> None:
    parsed = parse_release_title("Anime Title：TV+OVA; The Story")

    assert parsed is not None
    assert parsed.is_mixed_collection
    assert "The Story" in _title_text(parsed)


def test_mixed_content_date_context_does_not_consume_a_real_subtitle() -> None:
    parsed = parse_release_title("Anime Title：TV+OVA (The Story 2025-11-12)")

    assert parsed is not None
    assert parsed.is_mixed_collection
    assert "The Story" in _title_text(parsed)


@pytest.mark.parametrize(
    "raw",
    (
        "[TV+OVA] 86 [1080p]",
        "86：[TV+OVA] [1080p]",
        "86: [TV+OVA] [1080p]",
    ),
)
def test_mixed_collection_preserves_a_numeric_work_title(raw: str) -> None:
    parsed = parse_release_title(raw)

    assert parsed is not None
    assert parsed.is_mixed_collection
    assert parsed.primary_title == "86"
    assert parsed.episode is None
    assert "episode" not in parsed.evidence


@pytest.mark.parametrize(
    "raw",
    (
        "[TV+OVA][1080p]",
        "[APTX4869][CONAN][名侦探柯南 1045&1046 降下天罚的生日派对]" "[TV+OVA][1080p]",
    ),
)
def test_titleless_mixed_structure_is_still_materialized(raw: str) -> None:
    parsed = parse_release_title(raw)

    assert parsed is not None
    assert parsed.primary_title is None
    assert parsed.is_mixed_collection
    assert parsed.episode is None


def test_mixed_root_metadata_tail_accepts_inline_date() -> None:
    raw = "Fushigi Yugi_TV+OVA+Manga_dub jpn sub cht_2025-11-12"

    parsed = parse_release_title(raw)

    assert parsed is not None
    assert parsed.is_mixed_collection
    assert parsed.title_en == "Fushigi Yugi"
    assert parsed.subtitle is not None
    assert parsed.subtitle.casefold() == "cht"


def test_mixed_collection_does_not_expose_external_episode_claim() -> None:
    parsed = parse_release_title("[TV + OVA] Anime Title - 01 [1080p]")

    assert parsed is not None
    assert parsed.is_mixed_collection
    assert parsed.episode is None
    assert parsed.episode_end is None
    assert "episode" not in parsed.evidence


@pytest.mark.parametrize(
    "raw",
    (
        "[TV-OVA-Fansub] Anime - 01",
        "[Group] Anime OVA01 [1080p]",
        "[Group] Anime OVA01-02 [1080p]",
        "[Group] Anime S01E03 - TV + OVA Discussion [1080p]",
        "[Group] Anime EP03 - TV + OVA [1080p]",
        "[Group] Anime TV 01-12 [1080p]",
        "Anime Title：SP+Special",
        "Anime Title：TV+TV Anime",
        "Anime - 01 (Alt_TV+OVA) [1080p]",
        "Anime - 01 (Alt:TV+OVA) [1080p]",
        "[Group] Anime - 01 [Tag_TV+OVA] [1080p]",
        "[Group] Anime - 01 [Tag:TV+OVA] [1080p]",
        "[TV+OVA_Fansub] Anime - 01 [1080p]",
    ),
)
def test_mixed_content_manifest_requires_metadata_shaped_context(raw: str) -> None:
    parsed = parse_release_title(raw)

    assert parsed is not None
    assert not parsed.is_mixed_collection


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


def test_rejected_structural_marker_inside_group_does_not_infer_media() -> None:
    parsed = parse_release_title("[S02E05-Fansub] Plain Anime Title [1080p]")

    assert parsed is not None
    assert parsed.group == "S02E05-Fansub"
    assert parsed.episode is None
    assert parsed.media_type is MediaType.UNKNOWN


def test_shadowed_episode_title_candidate_does_not_remove_title_text() -> None:
    raw = "[Group] Anime S01E01 Season 2 Episode 3 - Another Title " "[1080p]"

    parsed = parse_release_title(raw)

    assert parsed is not None
    assert parsed.season == 1
    assert parsed.episode == 1
    assert "Another Title" in _title_text(parsed)
    assert "episode-title" not in parsed.evidence


def test_resolved_evidence_excludes_shadowed_special_candidate() -> None:
    parsed = parse_release_title("[Group] Anime OVA01 OAD02 [1080p]")

    assert parsed is not None
    assert parsed.media_type is MediaType.OVA
    assert "ova" in parsed.evidence
    assert "oad" not in parsed.evidence


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
    ("raw", "episode"),
    (
        ("[Group] Room No. 01 ~ 02 - 03 [1080p]", 3),
        ("[Group] Room EP01 ~ EP02 - 03 [1080p]", 3),
        ("[Group] Anime EP03 - Review EP01 ~ EP02 [1080p]", 3),
        ("[EP01 ~ EP02-Fansub] Anime Title - 03 [1080p]", 3),
        ("[Group][S01E03] Anime - Review EP01 ~ EP02 [1080p]", 3),
    ),
)
def test_spaced_numbers_in_titles_or_groups_are_not_episode_ranges(
    raw: str, episode: int
) -> None:
    parsed = parse_release_title(raw)

    assert parsed is not None
    assert parsed.episode == episode
    assert parsed.episode_end is None
    assert parsed.release_kind is ReleaseKind.SINGLE


def test_explicit_range_allows_a_same_segment_year_suffix() -> None:
    parsed = parse_release_title("[Group] Anime EP01 ~ EP02 - 2025 [1080p]")

    assert parsed is not None
    assert parsed.episode == 1
    assert parsed.episode_end == 2
    assert parsed.release_kind is ReleaseKind.RANGE
    assert parsed.year == 2025


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
