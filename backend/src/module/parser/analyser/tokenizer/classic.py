"""Generic, evidence-oriented parser for anime resource names.

Unlike the former ordered mutation pipeline, this module never reclassifies an
entire title fragment because it contains one marker.  It records exact matched
spans, removes only those spans, and reconstructs titles from the remaining
text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .normalization import normalize
from .result import MediaType, ParsedRelease, ReleaseKind

_TITLE_CHAR = re.compile(r"[A-Za-z\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff]")
_HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_PURE_HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+")
_KANA = re.compile(r"[\u3040-\u30ff]")
_LATIN = re.compile(r"[A-Za-z]")
_NUMERIC_TITLE = re.compile(r"\d{1,3}(?:\s*[/.-]\s*\d{1,3})?")

_DATE = re.compile(r"(?<!\d)(?:19|20)\d{2}[.\-/]\d{1,2}[.\-/]\d{1,2}(?!\d)")
_YEAR = re.compile(r"(?<!\d)((?:18|19|20|21)\d{2})(?!\d)")
_FILE_SIZE = re.compile(r"(?<!\w)\d+(?:\.\d+)?\s*[KMGT]i?B(?!\w)", re.I)
_HASH = re.compile(r"(?<![0-9A-F])[0-9A-F]{8}(?![0-9A-F])", re.I)

_RANGE = re.compile(
    r"(?<![\w.])(?:E(?:P)?\.?\s*)?(\d{1,4}(?:\.\d+)?)\s*"
    r"(?:-|~|～|—)\s*(?:E(?:P)?\.?\s*)?(\d{1,4}(?:\.\d+)?)"
    r"(?:v(\d+))?(?![\w.])",
    re.I,
)
_SEASON_EPISODE = re.compile(
    r"(?<!\w)S(\d{1,2})\s*E(?:P)?\.?\s*(\d{1,4}(?:\.\d+)?)" r"(?:v(\d+))?(?!\w)",
    re.I,
)
_SEASON_EPISODE_WORDS = re.compile(
    r"\bSeason\s+(\d{1,2})\s+(?:Episode|EP?\.?)\s*" r"(\d{1,4}(?:\.\d+)?)(?:v(\d+))?\b",
    re.I,
)
_SEASON = re.compile(r"(?<!\w)(S\d{1,2}|Season\s+\d{1,2})(?!\w)", re.I)
_ORDINAL_SEASON = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)\s+Season\b", re.I)
_CHINESE_SEASON = re.compile(r"第([零〇一二两三四五六七八九十百\d]+)[季期]")
_EXPLICIT_EPISODE = re.compile(
    r"(?<!\w)(?:Episode|EP?\.?|#)\s*[-_. ]?\s*" r"(\d{1,4}(?:\.\d+)?)(?:v(\d+))?(?!\w)",
    re.I,
)
_CHINESE_EPISODE = re.compile(r"(?:第\s*)?(\d{1,4}(?:\.\d+)?)\s*[话話集]")
_FULL_COLLECTION = re.compile(r"全\s*(\d{1,4})\s*[话話集]")
_PRE_EPISODE = re.compile(r"^\s*(\d{1,4})Pre\s*$", re.I)
_COMPOUND_EPISODE = re.compile(r"^\s*(\d{1,4})\(\d+\)\s*$")
_ATLAS_EPISODE = re.compile(r"^\s*(\d{1,4})_(?:.*[\u3040-\u30ff\u3400-\u9fff].*)$")
_BARE_EPISODE = re.compile(r"^\s*-?\s*(\d{1,4}(?:\.\d+)?)(?:v(\d+))?\s*$", re.I)
_TRAILING_EPISODE = re.compile(
    r"(?:\s+-\s*|(?<=[^\d\s])-\s*|\s+)(\d{1,4}(?:\.\d+)?)(?:v(\d+))?\s*$",
    re.I,
)

_SPECIAL_NUMBER = re.compile(
    r"(?<![A-Za-z0-9])(OVA|OAD|SP|Special)\s*(?:[-_.]\s*)?"
    r"(\d{1,4}(?:\.\d+)?)(?:v(\d+))?(?![A-Za-z0-9])",
    re.I,
)
_SPECIAL_WORD = re.compile(r"(?<![A-Za-z0-9])(OVA|OAD|SP|Special)(?![A-Za-z0-9])", re.I)
_SPECIAL_CJK = re.compile(r"番外篇?|特別篇|特别篇")
_PV = re.compile(
    r"(?<![A-Za-z0-9])(PV|CM)(?:\s*[-_.]?\s*(\d{1,3}))?(?![A-Za-z0-9=])",
    re.I,
)
_NCOP = re.compile(r"(?<![A-Za-z0-9])NCOP(?:v?(\d+))?(?![A-Za-z0-9])", re.I)
_NCED = re.compile(r"(?<![A-Za-z0-9])NCED(?:v?(\d+))?(?![A-Za-z0-9])", re.I)
_MOVIE_CJK = re.compile(r"劇場版?|剧场版?|電影版|电影版")
_MOVIE_ROMAJI = re.compile(r"(?<!\w)Gekijou-?ban(?!\w)", re.I)
_MOVIE_EN = re.compile(r"(?<!\w)(?:The\s+)?Movie(?!\w)", re.I)

_BATCH = re.compile(
    r"(?<!\w)(?:Complete(?:\s+(?:Series|Season))?(?:\s+Batch)?|Batch)(?!\w)",
    re.I,
)
_COLLECTION = re.compile(r"合集|全集|全[话話集]|总集篇|總集篇|特典")

_RESOLUTION = re.compile(
    r"(?<![A-Za-z0-9])(?:\d{3,4}[xX]\d{3,4}|(?:720|1080|2160)[pP](?:60)?|4[Kk])(?![A-Za-z0-9])"
)
_SOURCE = re.compile(
    r"(?<!\w)(?:WEB[-_. ]?DL(?:\s+Remux)?|WebRip|BDRip|BluRay|Blu-Ray|"
    r"B-Global|Baha|Bilibili|AT-X|TTFC|CR|ADN|iQIYI|Abema|AMZN|NF|"
    r"HDTV|DVD|Remux|WEB)(?!\w)",
    re.I,
)
_CODEC = re.compile(
    r"(?<![A-Za-z0-9])(?:HEVC(?:[-_. ]?10[- ]?bit)?|AVC|x26[45]|H\.?26[45]|"
    r"(?:8|10|12)bit|Ma10p)(?![A-Za-z0-9])",
    re.I,
)
_AUDIO = re.compile(
    r"(?<![A-Za-z0-9])(?:AAC|FLAC|MP3|AC-?3|E-?AC-?3|DDP(?:\d(?:\.\d)?)?|"
    r"DTS|Opus|Dual[-_ ]?Audio)(?![A-Za-z0-9])",
    re.I,
)
_CONTAINER = re.compile(r"(?<![A-Za-z0-9])(MP4|MKV|AVI)(?![A-Za-z0-9])", re.I)
_SUBTITLE = re.compile(
    r"(?<![A-Za-z0-9])(?:CHS(?:_JP)?|CHT(?:_JP)?|GB(?:_(?:JP|MP4|MKV))?|Big5|"
    r"VOSTFR|ENG|Multi[-_ ]?Subs?|Multiple[-_ ]?Subtitles?|ASSx2|PGS)"
    r"(?![A-Za-z0-9])",
    re.I,
)
_CJK_SUBTITLE_TAG = re.compile(
    r"[简簡繁日英中字幕体體双雙语語内內封嵌外挂掛多国國]+(?:PGS)?", re.I
)
_VERSION = re.compile(r"(?<!\w)[vV](\d+)(?!\w)")
_PREFIX = re.compile(r"^\s*(?:★?\s*\d{1,2}月新番\s*★?|★?\s*新番\s*★?)")
_RECRUIT = re.compile(r"[（(]?(?:字幕社?)?招[募人].*[）)]?$|急招翻校轴|搜索用[：:].*$")
_REGION = re.compile(r"[（(](?:仅限)?港澳台地区[）)]")
_DUB = re.compile(r"(?:配音版|Dub)", re.I)
_TRAILING_RELEASE_GROUP = re.compile(r"\s*-[\w·&.-]+(?:Raws?|Subs?)\s*$", re.I)


@dataclass(frozen=True, slots=True)
class _Segment:
    text: str
    start: int
    end: int
    enclosure: str | None = None


class _WorkingSegment:
    def __init__(self, segment: _Segment):
        self.segment = segment
        self.mask = [False] * len(segment.text)

    def available(self, match: re.Match[str]) -> bool:
        return not any(self.mask[match.start() : match.end()])

    def consume(self, match: re.Match[str]) -> None:
        self.mask[match.start() : match.end()] = [True] * (match.end() - match.start())

    def consume_span(self, start: int, end: int) -> None:
        self.mask[start:end] = [True] * (end - start)

    def residual(self) -> str:
        return "".join(
            " " if used else char for char, used in zip(self.segment.text, self.mask)
        )


@dataclass(slots=True)
class _State:
    raw: str
    group: str | None = None
    season: int | None = None
    season_raw: str | None = None
    episode: int | float | None = None
    episode_end: int | float | None = None
    episode_title: str | None = None
    episode_priority: int = -1
    media_type: MediaType = MediaType.UNKNOWN
    media_priority: int = -1
    release_kind: ReleaseKind = ReleaseKind.SINGLE
    resolution: str | None = None
    source: str | None = None
    subtitle: str | None = None
    codecs: list[str] = field(default_factory=list)
    audio: list[str] = field(default_factory=list)
    container: str | None = None
    version: int | None = None
    year: int | None = None
    tags: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    def set_episode(
        self,
        episode: int | float,
        *,
        priority: int,
        end: int | float | None = None,
        version: int | None = None,
    ) -> None:
        if priority >= self.episode_priority:
            self.episode = episode
            self.episode_end = end
            self.episode_priority = priority
            if version is not None:
                self.version = version

    def set_media(self, media_type: MediaType, priority: int) -> None:
        if priority > self.media_priority:
            self.media_type = media_type
            self.media_priority = priority


def parse_release_title(raw: str) -> ParsedRelease | None:
    """Parse a resource name without requiring an episode number."""
    if not raw or not raw.strip():
        return None

    normalized = normalize(raw)
    segments = _scan_segments(normalized)
    if not segments:
        return None

    state = _State(raw=raw)
    group_indices = _find_group_segments(segments)
    if group_indices:
        state.group = "&".join(segments[index].text.strip() for index in group_indices)
        state.evidence.append("group")

    working = [_WorkingSegment(segment) for segment in segments]
    for index in group_indices:
        working[index].mask[:] = [True] * len(working[index].mask)

    _preclassify_movie(working, state)
    _extract_numbers(working, state)
    _extract_media_and_cardinality(working, state)
    _extract_technical_metadata(working, state)

    title_en, title_zh, title_jp = _reconstruct_titles(working)
    if not any((title_en, title_zh, title_jp)):
        return None

    if state.media_type is MediaType.UNKNOWN:
        if state.episode is not None or state.release_kind is not ReleaseKind.SINGLE:
            state.set_media(MediaType.EPISODE, 0)

    return ParsedRelease(
        raw=raw,
        title_en=title_en,
        title_zh=title_zh,
        title_jp=title_jp,
        group=state.group,
        season=state.season,
        season_raw=state.season_raw,
        episode=state.episode,
        episode_end=state.episode_end,
        episode_title=state.episode_title,
        media_type=state.media_type,
        release_kind=state.release_kind,
        resolution=state.resolution,
        source=state.source,
        subtitle=state.subtitle,
        codecs=tuple(state.codecs),
        audio=tuple(state.audio),
        container=state.container,
        version=state.version,
        year=state.year,
        tags=tuple(state.tags),
        evidence=tuple(state.evidence),
    )


def _scan_segments(text: str) -> list[_Segment]:
    segments: list[_Segment] = []
    free_start = 0
    index = 0
    bracket_pairs = {"[": "]", "(": ")"}

    def add_free(start: int, end: int) -> None:
        content = text[start:end]
        if content.strip():
            segments.append(_Segment(content, start, end))

    while index < len(text):
        opener = text[index]
        if opener not in bracket_pairs:
            index += 1
            continue
        add_free(free_start, index)
        closer = bracket_pairs[opener]
        depth = 1
        cursor = index + 1
        while cursor < len(text) and depth:
            if text[cursor] == opener:
                depth += 1
            elif text[cursor] == closer:
                depth -= 1
            cursor += 1
        content_end = cursor - 1 if depth == 0 else len(text)
        content = text[index + 1 : content_end]
        if content.strip():
            enclosure = "square" if opener == "[" else "round"
            segments.append(_Segment(content, index, cursor, enclosure))
        index = cursor
        free_start = cursor

    add_free(free_start, len(text))
    return segments


def _find_group_segments(segments: list[_Segment]) -> set[int]:
    if not segments or segments[0].enclosure != "square":
        return set()
    first = segments[0].text.strip()
    if _looks_like_metadata(first):
        return set()

    has_free_title = any(
        segment.enclosure is None
        and _contains_title(segment.text)
        and not _looks_like_metadata(segment.text)
        for segment in segments[1:]
    )
    if not (_looks_like_group(first) or has_free_title):
        return set()

    indices = {0}
    for index, segment in enumerate(segments[1:], 1):
        if segment.enclosure != "square" or not _looks_like_group(segment.text):
            break
        indices.add(index)
    return indices


def _looks_like_group(text: str) -> bool:
    value = text.strip()
    lower = value.lower()
    if re.search(r"字幕[组組社]?|搬运|搬運|压制|壓制|发布|發佈", value):
        return True
    if re.search(r"raws?|fansub|subs?|house|studio|group|team|rip", lower):
        return True
    if lower in {"ani", "official", "magicstar", "doomdos", "vcb-studio"}:
        return True
    if "&" in value and len(value) <= 48:
        return True
    return bool(
        len(value) <= 16 and " " not in value and re.fullmatch(r"[A-Z0-9.-]+", value)
    )


def _looks_like_metadata(text: str) -> bool:
    value = text.strip()
    if not value:
        return True
    structural_patterns = (
        _RANGE,
        _SEASON_EPISODE,
        _SEASON_EPISODE_WORDS,
        _SEASON,
        _CHINESE_SEASON,
        _FULL_COLLECTION,
        _CHINESE_EPISODE,
        _BARE_EPISODE,
        _SPECIAL_NUMBER,
        _SPECIAL_WORD,
        _SPECIAL_CJK,
        _PV,
        _NCOP,
        _NCED,
        _MOVIE_CJK,
        _MOVIE_ROMAJI,
        _MOVIE_EN,
        _BATCH,
        _COLLECTION,
        _DATE,
        _YEAR,
        _FILE_SIZE,
    )
    if any(pattern.fullmatch(value) for pattern in structural_patterns):
        return True
    if _CJK_SUBTITLE_TAG.fullmatch(value) or value.lower() in {"end", "生"}:
        return True

    residual = value
    technical_patterns = (
        _RESOLUTION,
        _SOURCE,
        _CODEC,
        _AUDIO,
        _CONTAINER,
        _SUBTITLE,
    )
    for pattern in technical_patterns:
        residual = pattern.sub(" ", residual)
    residual = re.sub(r"[\s_+.,-]+", "", residual)
    return not _contains_title(residual)


def _contains_title(text: str) -> bool:
    return bool(_TITLE_CHAR.search(text))


def _contains_title_fragment(text: str) -> bool:
    return _contains_title(text) or bool(_NUMERIC_TITLE.fullmatch(text.strip()))


def _number(value: str) -> int | float:
    number = float(value)
    return int(number) if number.is_integer() else number


def _is_year_number(value: str) -> bool:
    return value.isdigit() and len(value) == 4 and 1800 <= int(value) <= 2199


def _consume_all(work: _WorkingSegment, pattern: re.Pattern[str]):
    for match in pattern.finditer(work.segment.text):
        if work.available(match):
            yield match


def _preclassify_movie(working: list[_WorkingSegment], state: _State) -> None:
    """Record strong movie evidence before resolving ambiguous trailing numbers."""
    for work in working:
        for pattern in (_MOVIE_CJK, _MOVIE_ROMAJI):
            if any(True for _ in _consume_all(work, pattern)):
                state.set_media(MediaType.MOVIE, 100)
                return
        for match in _consume_all(work, _MOVIE_EN):
            after = work.segment.text[match.end() :].lstrip()
            if not re.match(r"[A-Za-z]", after):
                state.set_media(MediaType.MOVIE, 100)
                return


def _is_metadata_tail(text: str) -> bool:
    residual = text
    for pattern in (
        _RESOLUTION,
        _SOURCE,
        _CODEC,
        _AUDIO,
        _CONTAINER,
        _SUBTITLE,
        _TRAILING_EPISODE,
    ):
        residual = pattern.sub(" ", residual)
    residual = re.sub(r"[\s_+.,\-–—]+", "", residual)
    return not _contains_title(residual)


def _extract_episode_title(
    work: _WorkingSegment, match: re.Match[str], state: _State
) -> None:
    """Separate Emby/Plex ``Series - SxxExx - Episode title`` layouts."""
    before = work.segment.text[: match.start()]
    separator = re.search(r"\s+-\s*$", before)
    if separator:
        work.consume_span(separator.start(), match.start())

    after = work.segment.text[match.end() :]
    episode_title = re.fullmatch(r"\s*-\s*(.+?)\s*", after)
    if episode_title and _contains_title_fragment(episode_title.group(1)):
        state.episode_title = _clean_title(episode_title.group(1))
        work.consume_span(match.end(), len(work.segment.text))
        state.evidence.append("episode-title")


def _extract_numbers(working: list[_WorkingSegment], state: _State) -> None:
    for work in working:
        text = work.segment.text

        for match in _consume_all(work, _DATE):
            work.consume(match)
            state.tags.append(match.group())

        for match in _consume_all(work, _FILE_SIZE):
            work.consume(match)
            state.tags.append(match.group())

        for match in _consume_all(work, _YEAR):
            if match.group() == text.strip() or _is_metadata_tail(text[match.end() :]):
                work.consume(match)
                state.year = int(match.group(1))
                state.evidence.append("year")

        for match in _consume_all(work, _RANGE):
            start, end = _number(match.group(1)), _number(match.group(2))
            prefix = text[: match.start()]
            suffix = text[match.end() :]
            compact = bool(
                re.search(r"\d(?:-|~|～|—)(?:E(?:P)?\.?)?\d", match.group(), re.I)
            )
            isolated = not _contains_title(prefix + suffix)
            labelled = bool(re.search(r"(?:Episodes?|Eps?)\s*$", prefix, re.I))
            if (
                start >= 1800
                or end >= 1800
                or start > end
                or re.search(r"\d+\s*/\s*$", prefix)
                or not (compact or isolated or labelled)
            ):
                continue
            work.consume(match)
            state.set_episode(start, priority=85, end=end, version=_int(match.group(3)))
            state.release_kind = ReleaseKind.RANGE
            state.evidence.append("episode-range")

        for pattern in (_SEASON_EPISODE, _SEASON_EPISODE_WORDS):
            for match in _consume_all(work, pattern):
                work.consume(match)
                _extract_episode_title(work, match, state)
                state.season = int(match.group(1))
                state.season_raw = match.group(0)
                state.set_episode(
                    _number(match.group(2)),
                    priority=100,
                    version=_int(match.group(3)),
                )
                state.evidence.extend(("season", "episode"))

        for match in _consume_all(work, _SPECIAL_NUMBER):
            work.consume(match)
            media_type = _special_media(match.group(1))
            state.set_media(media_type, 80)
            state.set_episode(
                _number(match.group(2)),
                priority=80,
                version=_int(match.group(3)),
            )
            state.evidence.extend((media_type.value, "episode"))

        for match in _consume_all(work, _PV):
            if match.group(2) is None:
                continue
            work.consume(match)
            state.set_media(MediaType.PV, 60)
            state.set_episode(_number(match.group(2)), priority=75)
            state.evidence.extend(("pv", "episode"))

        for match in _consume_all(work, _SEASON):
            work.consume(match)
            raw_season = match.group(1)
            number_match = re.search(r"\d+", raw_season)
            if number_match:
                state.season = int(number_match.group())
                state.season_raw = raw_season
                state.evidence.append("season")

        for match in _consume_all(work, _CHINESE_SEASON):
            work.consume(match)
            state.season = _chinese_number(match.group(1))
            state.season_raw = match.group(0)
            state.evidence.append("season")

        for match in _consume_all(work, _ORDINAL_SEASON):
            if state.season is None:
                work.consume(match)
                state.season = int(match.group(1))
                state.season_raw = match.group(0)
                state.evidence.append("season")

        for match in _consume_all(work, _FULL_COLLECTION):
            work.consume(match)
            state.set_episode(1, priority=95, end=int(match.group(1)))
            state.release_kind = ReleaseKind.COLLECTION
            state.evidence.extend(("collection", "episode-range"))

        for match in _consume_all(work, _EXPLICIT_EPISODE):
            work.consume(match)
            state.set_episode(
                _number(match.group(1)), priority=90, version=_int(match.group(2))
            )
            state.evidence.append("episode")

        for match in _consume_all(work, _CHINESE_EPISODE):
            work.consume(match)
            state.set_episode(_number(match.group(1)), priority=90)
            state.evidence.append("episode")

        for pattern in (_PRE_EPISODE, _COMPOUND_EPISODE, _ATLAS_EPISODE):
            match = pattern.match(text)
            if match and work.available(match):
                work.consume(match)
                state.set_episode(_number(match.group(1)), priority=75)
                state.evidence.append("episode")

        trailing = _TRAILING_EPISODE.search(text)
        if (
            trailing
            and work.available(trailing)
            and not _is_year_number(trailing.group(1))
            and state.media_type is not MediaType.MOVIE
        ):
            work.consume(trailing)
            state.set_episode(
                _number(trailing.group(1)),
                priority=70,
                version=_int(trailing.group(2)),
            )
            state.evidence.append("episode")

        bare = _BARE_EPISODE.match(text)
        if (
            bare
            and work.available(bare)
            and not _is_year_number(bare.group(1))
            and state.media_type is not MediaType.MOVIE
        ):
            work.consume(bare)
            state.set_episode(
                _number(bare.group(1)), priority=70, version=_int(bare.group(2))
            )
            state.evidence.append("episode")


def _extract_media_and_cardinality(
    working: list[_WorkingSegment], state: _State
) -> None:
    for work in working:
        text = work.segment.text

        for match in _consume_all(work, _MOVIE_CJK):
            work.consume(match)
            state.set_media(MediaType.MOVIE, 100)
            state.evidence.append("movie")
        for match in _consume_all(work, _MOVIE_ROMAJI):
            work.consume(match)
            state.set_media(MediaType.MOVIE, 100)
            state.evidence.append("movie")
        for match in _consume_all(work, _MOVIE_EN):
            before = text[: match.start()].rstrip()
            after = text[match.end() :].lstrip()
            marker_is_edge = (
                not before or not after or work.segment.enclosure == "square"
            )
            followed_by_title_word = bool(re.match(r"[A-Za-z]", after))
            if followed_by_title_word:
                continue
            if not marker_is_edge and state.episode is not None:
                continue
            work.consume(match)
            state.set_media(MediaType.MOVIE, 100)
            state.evidence.append("movie")

        for match in _consume_all(work, _SPECIAL_WORD):
            after = text[match.end() :].lstrip()
            if re.match(r"[A-Za-z]", after):
                continue
            media_type = _special_media(match.group(1))
            work.consume(match)
            state.set_media(media_type, 80)
            state.evidence.append(media_type.value)

        for match in _consume_all(work, _SPECIAL_CJK):
            work.consume(match)
            state.set_media(MediaType.SPECIAL, 80)
            state.evidence.append("special")

        for match in _consume_all(work, _PV):
            work.consume(match)
            state.set_media(MediaType.PV, 60)
            state.evidence.append("pv")
        for match in _consume_all(work, _NCOP):
            work.consume(match)
            state.set_media(MediaType.OPENING, 60)
            state.version = state.version or _int(match.group(1))
            state.evidence.append("opening")
        for match in _consume_all(work, _NCED):
            work.consume(match)
            state.set_media(MediaType.ENDING, 60)
            state.version = state.version or _int(match.group(1))
            state.evidence.append("ending")

        for match in _consume_all(work, _BATCH):
            work.consume(match)
            state.release_kind = ReleaseKind.BATCH
            state.evidence.append("batch")
        for match in _consume_all(work, _COLLECTION):
            work.consume(match)
            state.release_kind = ReleaseKind.COLLECTION
            state.evidence.append("collection")


def _extract_technical_metadata(working: list[_WorkingSegment], state: _State) -> None:
    for work in working:
        text = work.segment.text

        for match in _consume_all(work, _RESOLUTION):
            work.consume(match)
            state.resolution = state.resolution or match.group()
            state.evidence.append("resolution")
        for match in _consume_all(work, _SOURCE):
            work.consume(match)
            state.source = state.source or match.group()
            state.evidence.append("source")
        for match in _consume_all(work, _CODEC):
            work.consume(match)
            _append_unique(state.codecs, match.group())
        for match in _consume_all(work, _AUDIO):
            work.consume(match)
            _append_unique(state.audio, match.group())
        for match in _consume_all(work, _SUBTITLE):
            work.consume(match)
            state.subtitle = _prefer_subtitle(state.subtitle, match.group())
            container = re.search(r"_(MP4|MKV)$", match.group(), re.I)
            if container:
                state.container = state.container or container.group(1)
        for match in _consume_all(work, _CONTAINER):
            work.consume(match)
            state.container = state.container or match.group(1)

        if work.segment.enclosure == "square":
            subtitle_tag = _clean_fragment(work.residual())
            if _CJK_SUBTITLE_TAG.fullmatch(subtitle_tag):
                work.mask[:] = [True] * len(work.mask)
                state.subtitle = _prefer_subtitle(state.subtitle, subtitle_tag)
            if _DUB.search(text):
                work.mask[:] = [True] * len(work.mask)
                state.tags.append(text.strip())

        for match in _consume_all(work, _VERSION):
            work.consume(match)
            state.version = state.version or int(match.group(1))
        for pattern in (_PREFIX, _RECRUIT, _REGION, _TRAILING_RELEASE_GROUP):
            for match in _consume_all(work, pattern):
                work.consume(match)
                state.tags.append(match.group().strip())
        for match in _consume_all(work, _HASH):
            work.consume(match)
            state.tags.append(match.group())

        _extract_episode_after_metadata(work, state)

        residual = _clean_fragment(work.residual())
        if work.segment.enclosure in {"square", "round"} and residual.lower() in {
            "end",
            "生",
        }:
            work.mask[:] = [True] * len(work.mask)
            state.tags.append(residual)


def _extract_episode_after_metadata(work: _WorkingSegment, state: _State) -> None:
    """Resolve episode numbers mixed into an enclosed technical tag."""
    if (
        state.episode is not None
        or state.media_type is MediaType.MOVIE
        or work.segment.enclosure != "square"
    ):
        return
    residual = work.residual()
    match = _BARE_EPISODE.match(residual) or _TRAILING_EPISODE.search(residual)
    if not match or _is_year_number(match.group(1)):
        return
    work.consume_span(match.start(), match.end())
    state.set_episode(
        _number(match.group(1)), priority=65, version=_int(match.group(2))
    )
    state.evidence.append("episode")


def _reconstruct_titles(
    working: list[_WorkingSegment],
) -> tuple[str | None, str | None, str | None]:
    fragments: list[str] = []
    for work in working:
        residual = _clean_fragment(work.residual())
        if not residual or not _contains_title_fragment(residual):
            continue
        if work.segment.enclosure == "round":
            residual = f"({residual})"
        fragments.extend(_split_explicit_titles(residual))

    titles: dict[MediaType | str, list[str]] = {"en": [], "zh": [], "jp": []}
    for fragment in fragments:
        for part in _split_mixed_title(fragment):
            cleaned = _clean_title(part)
            if not cleaned or not _contains_title_fragment(cleaned):
                continue
            language = _title_language(cleaned)
            if cleaned not in titles[language]:
                titles[language].append(cleaned)

    return (
        _join_title_parts(titles["en"]),
        _join_title_parts(titles["zh"]),
        _join_title_parts(titles["jp"]),
    )


def _split_explicit_titles(text: str) -> list[str]:
    spaced = [part.strip() for part in re.split(r"\s+[/|]\s+", text) if part.strip()]
    if len(spaced) > 1:
        return spaced

    for match in re.finditer(r"/", text):
        left, right = text[: match.start()].strip(), text[match.end() :].strip()
        if not left or not right:
            continue
        if left[-1].isdigit() or right[0].isdigit():
            continue
        if _title_language(left) != _title_language(right):
            return [left, right]
    return [text]


def _split_mixed_title(text: str) -> list[str]:
    underscore = re.split(r"_(?=[A-Za-z\u3040-\u30ff\u3400-\u9fff])", text, maxsplit=1)
    if len(underscore) == 2 and _title_language(underscore[0]) != _title_language(
        underscore[1]
    ):
        return underscore

    cjk_to_latin = re.search(
        r"(?<=[\u3040-\u30ff\u3400-\u9fff])\s*[-–—]\s*(?=[A-Z][A-Za-z]+\s+[A-Za-z])",
        text,
    )
    if cjk_to_latin:
        return [text[: cjk_to_latin.start()], text[cjk_to_latin.end() :]]

    words = text.split()
    if len(words) < 2:
        runs: list[tuple[str, int]] = []
        for index, char in enumerate(text):
            language = (
                "en"
                if _LATIN.match(char)
                else "cjk" if (_HAN.match(char) or _KANA.match(char)) else None
            )
            if language is not None and (not runs or runs[-1][0] != language):
                runs.append((language, index))
        if len(runs) == 2 and runs[0][0] == "en":
            boundary = runs[1][1]
            return [text[:boundary], text[boundary:]]
        return [text]

    classes = [_word_language(word) for word in words]
    if words[0].isdigit() and classes[1] in {"zh", "jp"}:
        return [text]
    if words[-1].isdigit() and classes[0] in {"zh", "jp"}:
        return [text]
    transitions = [
        index
        for index in range(1, len(classes))
        if classes[index] != classes[index - 1]
    ]
    if len(transitions) == 1:
        index = transitions[0]
        return [" ".join(words[:index]), " ".join(words[index:])]
    if _PURE_HAN.fullmatch(words[0]) and "jp" in classes[1:] and classes[-1] == "en":
        jp_index = classes.index("jp")
        en_index = next(
            (
                index
                for index in range(jp_index + 1, len(classes))
                if classes[index] == "en"
            ),
            -1,
        )
        if en_index > jp_index:
            return [
                words[0],
                " ".join(words[1:en_index]),
                " ".join(words[en_index:]),
            ]
    return [text]


def _word_language(text: str) -> str:
    if _KANA.search(text):
        return "jp"
    if _HAN.search(text):
        return "zh"
    return "en"


def _title_language(text: str) -> str:
    if _KANA.search(text):
        return "jp"
    if _HAN.search(text):
        return "zh"
    return "en"


def _clean_fragment(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^(?:[-–—]\s+)+|(?:\s+[-–—])+$", "", text).strip()
    text = re.sub(r"^[\s_|]+|[\s_|]+$", "", text).strip()
    text = re.sub(r"^/\s*|\s*/$", "", text).strip()
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(text: str) -> str:
    text = _clean_fragment(text)
    return re.sub(r"_+", " ", text).strip()


def _join_title_parts(parts: list[str]) -> str | None:
    return " ".join(parts).strip() if parts else None


def _mostly_metadata(text: str) -> bool:
    return bool(re.fullmatch(r"[\w\s+_.-]{1,48}", text))


def _prefer_subtitle(current: str | None, candidate: str) -> str:
    if current is None or _HAN.search(candidate):
        return re.sub(r"_(?:MP4|MKV)$", "", candidate, flags=re.I)
    return current


def _append_unique(values: list[str], value: str) -> None:
    if value.lower() not in {item.lower() for item in values}:
        values.append(value)


def _special_media(marker: str) -> MediaType:
    marker = marker.lower()
    if marker == "ova":
        return MediaType.OVA
    if marker == "oad":
        return MediaType.OAD
    return MediaType.SPECIAL


def _int(value: str | None) -> int | None:
    return int(value) if value is not None else None


def _chinese_number(value: str) -> int:
    if value.isdigit():
        return int(value)
    digits = {
        "零": 0,
        "〇": 0,
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    if "百" in value:
        left, _, right = value.partition("百")
        return digits.get(left, 1) * 100 + _chinese_number(right or "零")
    if "十" in value:
        left, _, right = value.partition("十")
        return digits.get(left, 1) * 10 + digits.get(right, 0)
    return digits.get(value, 1)
