"""Generic, evidence-oriented parser for anime resource names.

Unlike the former ordered mutation pipeline, this module never reclassifies an
entire title fragment because it contains one marker.  It records exact matched
spans, removes only those spans, and reconstructs titles from the remaining
text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .candidate import (
    Candidate,
    Claims,
    Observation,
    OverlapPolicy,
    ShadowedSpanPolicy,
    Span,
)
from .normalization import normalize
from .resolver import Resolution, resolve_candidates
from .result import MediaType, ParsedRelease, ReleaseKind
from .trace import ParseOutcome, ParseTrace, TraceSegment

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
_SEASON_EPISODE_RANGE = re.compile(
    r"(?<!\w)S(\d{1,2})\s*E(?:P)?\.?\s*(\d{1,4}(?:\.\d+)?)\s*"
    r"(?:-|~|～|—)\s*(?:E(?:P)?\.?\s*)?(\d{1,4}(?:\.\d+)?)"
    r"(?:v(\d+))?(?!\w)",
    re.I,
)
_SEASON_EPISODE_WORDS = re.compile(
    r"\bSeason\s+(\d{1,2})\s+(?:Episode|EP?\.?)\s*" r"(\d{1,4}(?:\.\d+)?)(?:v(\d+))?\b",
    re.I,
)
_SEASON_EPISODE_WORDS_RANGE = re.compile(
    r"\bSeason\s+(\d{1,2})\s+(?:Episodes?|EPs?\.?)\s*"
    r"(\d{1,4}(?:\.\d+)?)\s*(?:-|~|～|—)\s*"
    r"(?:E(?:P)?\.?\s*)?(\d{1,4}(?:\.\d+)?)(?:v(\d+))?\b",
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
_SPECIAL_RANGE = re.compile(
    r"(?<![A-Za-z0-9])(OVA|OAD|SP|Special)\s*(?:[-_.]\s*)?"
    r"(\d{1,4}(?:\.\d+)?)\s*(?:-|~|～|—)\s*"
    r"(?:\1\s*)?(\d{1,4}(?:\.\d+)?)(?:v(\d+))?(?![A-Za-z0-9])",
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


class _ResidualSegment:
    def __init__(self, segment: _Segment):
        self.segment = segment
        self.mask = [False] * len(segment.text)

    def mask_span(self, start: int, end: int) -> None:
        self.mask[start:end] = [True] * (end - start)

    def residual(self) -> str:
        return "".join(
            " " if used else char for char, used in zip(self.segment.text, self.mask)
        )


@dataclass(slots=True)
class _CandidateCollector:
    segments: list[_Segment]
    capture_observations: bool = False
    observations: list[Observation] = field(default_factory=list)
    candidates: list[Candidate] = field(default_factory=list)

    def add_span(
        self,
        *,
        rule_id: str,
        kind: str,
        segment_index: int,
        start: int,
        end: int,
        claims: Claims = Claims(),
        priority: int = 0,
        specificity: int = 0,
        evidence: tuple[str, ...] = (),
        extra_spans: tuple[Span, ...] = (),
        conflict_tags: frozenset[str] = frozenset(),
        blocks: frozenset[str] = frozenset(),
        preserve_as_title_on_conflict: bool = False,
        shadowed_span_policy: ShadowedSpanPolicy = ShadowedSpanPolicy.EXCLUDE,
        overlap_policy: OverlapPolicy = OverlapPolicy.EXCLUSIVE,
        captures: tuple[str | None, ...] = (),
    ) -> Candidate:
        span = Span(segment_index, start, end)
        suffix = f"{segment_index}:{start}:{end}"
        candidate_id = f"{rule_id}:{suffix}"
        observation_ids: tuple[str, ...] = ()
        if self.capture_observations:
            observation_id = f"observation:{candidate_id}"
            observation_ids = (observation_id,)
            self.observations.append(
                Observation(
                    id=observation_id,
                    rule_id=rule_id,
                    kind=kind,
                    span=span,
                    text=self.segments[segment_index].text[start:end],
                    captures=captures,
                )
            )
        candidate = Candidate(
            id=candidate_id,
            rule_id=rule_id,
            spans=(span, *extra_spans),
            claims=claims,
            priority=priority,
            specificity=specificity,
            observation_ids=observation_ids,
            evidence=evidence,
            conflict_tags=conflict_tags,
            blocks=blocks,
            preserve_as_title_on_conflict=preserve_as_title_on_conflict,
            shadowed_span_policy=shadowed_span_policy,
            shadowed_spans=(span,) if extra_spans else None,
            overlap_policy=overlap_policy,
        )
        self.candidates.append(candidate)
        return candidate

    def add_match(
        self,
        *,
        rule_id: str,
        kind: str,
        segment_index: int,
        match: re.Match[str],
        **kwargs: object,
    ) -> Candidate:
        return self.add_span(
            rule_id=rule_id,
            kind=kind,
            segment_index=segment_index,
            start=match.start(),
            end=match.end(),
            captures=match.groups(),
            **kwargs,  # type: ignore[arg-type]
        )

    def add_segments(
        self,
        *,
        rule_id: str,
        kind: str,
        segment_indices: tuple[int, ...],
        claims: Claims,
        priority: int,
        evidence: tuple[str, ...] = (),
    ) -> Candidate:
        spans = tuple(
            Span(index, 0, len(self.segments[index].text)) for index in segment_indices
        )
        observation_ids: list[str] = []
        if self.capture_observations:
            for span in spans:
                observation_id = (
                    f"observation:{rule_id}:{span.segment}:{span.start}:{span.end}"
                )
                observation_ids.append(observation_id)
                self.observations.append(
                    Observation(
                        id=observation_id,
                        rule_id=rule_id,
                        kind=kind,
                        span=span,
                        text=self.segments[span.segment].text,
                    )
                )
        candidate = Candidate(
            id=f"{rule_id}:" + ",".join(str(index) for index in segment_indices),
            rule_id=rule_id,
            spans=spans,
            claims=claims,
            priority=priority,
            observation_ids=tuple(observation_ids),
            evidence=evidence,
        )
        self.candidates.append(candidate)
        return candidate


def parse_release_title(raw: str) -> ParsedRelease | None:
    """Parse a resource name without requiring an episode number."""
    result, _ = _parse_release_title_with_candidates(raw, capture_trace=False)
    return result


def parse_release_title_with_trace(raw: str) -> ParseOutcome:
    """Parse a resource name together with immutable resolver diagnostics."""
    result, trace = _parse_release_title_with_candidates(raw, capture_trace=True)
    assert trace is not None
    return ParseOutcome(result=result, trace=trace)


def _parse_release_title_with_candidates(
    raw: str, *, capture_trace: bool
) -> tuple[ParsedRelease | None, ParseTrace | None]:
    normalized = normalize(raw) if raw and raw.strip() else ""
    segments = _scan_segments(normalized) if normalized else []
    if not segments:
        trace = ParseTrace(raw=raw, normalized=normalized) if capture_trace else None
        return None, trace

    collector = _CandidateCollector(segments, capture_observations=capture_trace)
    _collect_group_candidates(collector)
    _collect_structural_candidates(collector)
    _collect_media_candidates(collector)
    _collect_technical_candidates(collector)
    _collect_metadata_episode_candidates(collector)

    resolution = resolve_candidates(
        collector.candidates, collect_warnings=capture_trace
    )
    working = _working_from_spans(segments, resolution.excluded_spans)
    title_en, title_zh, title_jp = _reconstruct_titles(working)
    result = None
    if any((title_en, title_zh, title_jp)):
        result = _result_from_resolution(raw, title_en, title_zh, title_jp, resolution)

    trace = None
    if capture_trace:
        trace = ParseTrace.from_resolution(
            raw=raw,
            normalized=normalized,
            resolution=resolution,
            segments=_trace_segments(segments),
            observations=tuple(collector.observations),
            candidates=tuple(collector.candidates),
            residuals=tuple(work.residual() for work in working),
        )
    return result, trace


def _result_from_resolution(
    raw: str,
    title_en: str | None,
    title_zh: str | None,
    title_jp: str | None,
    resolution: Resolution,
) -> ParsedRelease:
    claims = resolution.claims
    media_type = claims.media_type
    if media_type is None and (
        claims.episode is not None or claims.release_kind is not None
    ):
        media_type = MediaType.EPISODE
    return ParsedRelease(
        raw=raw,
        title_en=title_en,
        title_zh=title_zh,
        title_jp=title_jp,
        group=claims.group,
        season=claims.season,
        season_raw=claims.season_raw,
        episode=claims.episode,
        episode_end=claims.episode_end,
        episode_title=claims.episode_title,
        media_type=media_type or MediaType.UNKNOWN,
        release_kind=claims.release_kind or ReleaseKind.SINGLE,
        resolution=claims.resolution,
        source=claims.source,
        subtitle=claims.subtitle,
        codecs=claims.codecs,
        audio=claims.audio,
        container=claims.container,
        version=claims.version,
        year=claims.year,
        tags=claims.tags,
        evidence=resolution.evidence,
    )


def _working_from_spans(
    segments: list[_Segment], excluded_spans: tuple[Span, ...]
) -> list[_ResidualSegment]:
    working = [_ResidualSegment(segment) for segment in segments]
    for span in excluded_spans:
        working[span.segment].mask_span(span.start, span.end)
    return working


def _trace_segments(segments: list[_Segment]) -> tuple[TraceSegment, ...]:
    traced: list[TraceSegment] = []
    for index, segment in enumerate(segments):
        enclosed = segment.enclosure is not None
        content_start = segment.start + 1 if enclosed else segment.start
        traced.append(
            TraceSegment(
                index=index,
                text=segment.text,
                outer_start=segment.start,
                outer_end=segment.end,
                content_start=content_start,
                content_end=content_start + len(segment.text),
                enclosure=segment.enclosure,
            )
        )
    return tuple(traced)


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
    if not segments:
        return set()

    first_free_title = next(
        (
            index
            for index, segment in enumerate(segments)
            if segment.enclosure is None
            and _contains_title_fragment(segment.text)
            and not _looks_like_metadata(segment.text)
        ),
        None,
    )
    has_free_title = first_free_title is not None

    group_index = next(
        (
            index
            for index, segment in enumerate(segments)
            if segment.enclosure == "square"
            and (first_free_title is None or index < first_free_title)
            and not _looks_like_metadata(segment.text)
            and (_looks_like_group(segment.text) or has_free_title)
        ),
        None,
    )
    if group_index is None:
        return set()

    indices = {group_index}
    for index, segment in enumerate(segments[group_index + 1 :], group_index + 1):
        if (
            segment.enclosure != "square"
            or _looks_like_metadata(segment.text)
            or not _looks_like_group(segment.text)
        ):
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
    if re.search(r"(?:^|[-_. ])fan(?:$|[-_. ])", lower):
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
        _SEASON_EPISODE_RANGE,
        _SEASON_EPISODE_WORDS_RANGE,
        _SEASON_EPISODE,
        _SEASON_EPISODE_WORDS,
        _SEASON,
        _CHINESE_SEASON,
        _FULL_COLLECTION,
        _CHINESE_EPISODE,
        _BARE_EPISODE,
        _SPECIAL_NUMBER,
        _SPECIAL_RANGE,
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


def _collect_group_candidates(collector: _CandidateCollector) -> set[int]:
    group_indices = _find_group_segments(collector.segments)
    if not group_indices:
        return set()
    ordered = tuple(sorted(group_indices))
    collector.add_segments(
        rule_id="group.square-prefix",
        kind="group",
        segment_indices=ordered,
        claims=Claims(
            group="&".join(collector.segments[index].text.strip() for index in ordered)
        ),
        priority=1000,
        evidence=("group",),
    )
    return group_indices


def _episode_title_parts(
    segment_index: int, text: str, match: re.Match[str]
) -> tuple[str | None, tuple[Span, ...]]:
    spans: list[Span] = []
    before = text[: match.start()]
    separator = re.search(r"\s+-\s*$", before)
    if separator:
        spans.append(Span(segment_index, separator.start(), match.start()))

    after = text[match.end() :]
    episode_title = re.fullmatch(r"\s*-\s*(.+?)\s*", after)
    if not episode_title or not _contains_title_fragment(episode_title.group(1)):
        return None, tuple(spans)
    spans.append(Span(segment_index, match.end(), len(text)))
    return _clean_title(episode_title.group(1)), tuple(spans)


def _collect_structural_candidates(collector: _CandidateCollector) -> None:
    for index, segment in enumerate(collector.segments):
        text = segment.text

        for match in _DATE.finditer(text):
            collector.add_match(
                rule_id="metadata.date",
                kind="tag",
                segment_index=index,
                match=match,
                claims=Claims(tags=(match.group(),)),
                priority=110,
            )

        for match in _FILE_SIZE.finditer(text):
            collector.add_match(
                rule_id="metadata.file-size",
                kind="tag",
                segment_index=index,
                match=match,
                claims=Claims(tags=(match.group(),)),
                priority=110,
            )

        for match in _YEAR.finditer(text):
            if match.group() != text.strip() and not _is_metadata_tail(
                text[match.end() :]
            ):
                continue
            collector.add_match(
                rule_id="metadata.year",
                kind="year",
                segment_index=index,
                match=match,
                claims=Claims(year=int(match.group(1))),
                priority=100,
                evidence=("year",),
            )

        for rule_id, pattern in (
            ("episode.season-range-compact", _SEASON_EPISODE_RANGE),
            ("episode.season-range-words", _SEASON_EPISODE_WORDS_RANGE),
        ):
            for match in pattern.finditer(text):
                start, end = _number(match.group(2)), _number(match.group(3))
                if start >= 1800 or end >= 1800 or start > end:
                    continue
                collector.add_match(
                    rule_id=rule_id,
                    kind="season-episode-range",
                    segment_index=index,
                    match=match,
                    claims=Claims(
                        season=int(match.group(1)),
                        season_raw=match.group(0),
                        episode=start,
                        episode_end=end,
                        release_kind=ReleaseKind.RANGE,
                        version=_int(match.group(4)),
                    ),
                    priority=105,
                    specificity=5,
                    evidence=("season", "episode-range"),
                )

        for match in _SPECIAL_RANGE.finditer(text):
            start, end = _number(match.group(2)), _number(match.group(3))
            if start >= 1800 or end >= 1800 or start > end:
                continue
            media_type = _special_media(match.group(1))
            collector.add_match(
                rule_id=f"episode.{media_type.value}-range",
                kind="special-episode-range",
                segment_index=index,
                match=match,
                claims=Claims(
                    episode=start,
                    episode_end=end,
                    media_type=media_type,
                    release_kind=ReleaseKind.RANGE,
                    version=_int(match.group(4)),
                ),
                priority=105,
                specificity=5,
                evidence=(media_type.value, "episode-range"),
            )

        for match in _RANGE.finditer(text):
            start, end = _number(match.group(1)), _number(match.group(2))
            prefix = text[: match.start()]
            suffix = text[match.end() :]
            compact = bool(
                re.search(r"\d(?:-|~|～|—)(?:E(?:P)?\.?\s*)?\d", match.group(), re.I)
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
            collector.add_match(
                rule_id="episode.range",
                kind="episode-range",
                segment_index=index,
                match=match,
                claims=Claims(
                    episode=start,
                    episode_end=end,
                    release_kind=ReleaseKind.RANGE,
                    version=_int(match.group(3)),
                ),
                priority=95,
                specificity=3,
                evidence=("episode-range",),
            )

        for rule_id, pattern in (
            ("episode.season-compact", _SEASON_EPISODE),
            ("episode.season-words", _SEASON_EPISODE_WORDS),
        ):
            for match in pattern.finditer(text):
                episode_title, extra_spans = _episode_title_parts(index, text, match)
                evidence: tuple[str, ...] = ("season", "episode")
                if episode_title:
                    evidence += ("episode-title",)
                collector.add_match(
                    rule_id=rule_id,
                    kind="season-episode",
                    segment_index=index,
                    match=match,
                    claims=Claims(
                        season=int(match.group(1)),
                        season_raw=match.group(0),
                        episode=_number(match.group(2)),
                        episode_title=episode_title,
                        version=_int(match.group(3)),
                    ),
                    priority=100,
                    specificity=4,
                    evidence=evidence,
                    extra_spans=extra_spans,
                )

        for match in _SPECIAL_NUMBER.finditer(text):
            media_type = _special_media(match.group(1))
            collector.add_match(
                rule_id=f"episode.{media_type.value}-numbered",
                kind="special-episode",
                segment_index=index,
                match=match,
                claims=Claims(
                    episode=_number(match.group(2)),
                    media_type=media_type,
                    version=_int(match.group(3)),
                ),
                priority=80,
                specificity=3,
                evidence=(media_type.value, "episode"),
            )

        for match in _PV.finditer(text):
            if match.group(2) is None:
                continue
            collector.add_match(
                rule_id="media.pv-numbered",
                kind="non-episode-video",
                segment_index=index,
                match=match,
                claims=Claims(episode=_number(match.group(2)), media_type=MediaType.PV),
                priority=75,
                specificity=2,
                evidence=("pv", "episode"),
            )

        for match in _SEASON.finditer(text):
            number_match = re.search(r"\d+", match.group(1))
            if number_match:
                collector.add_match(
                    rule_id="season.marker",
                    kind="season",
                    segment_index=index,
                    match=match,
                    claims=Claims(
                        season=int(number_match.group()), season_raw=match.group(1)
                    ),
                    priority=80,
                    evidence=("season",),
                )

        for match in _CHINESE_SEASON.finditer(text):
            collector.add_match(
                rule_id="season.chinese",
                kind="season",
                segment_index=index,
                match=match,
                claims=Claims(
                    season=_chinese_number(match.group(1)), season_raw=match.group(0)
                ),
                priority=80,
                evidence=("season",),
            )

        for match in _ORDINAL_SEASON.finditer(text):
            collector.add_match(
                rule_id="season.ordinal",
                kind="season",
                segment_index=index,
                match=match,
                claims=Claims(season=int(match.group(1)), season_raw=match.group(0)),
                priority=50,
                evidence=("season",),
                shadowed_span_policy=ShadowedSpanPolicy.KEEP,
            )

        for match in _FULL_COLLECTION.finditer(text):
            collector.add_match(
                rule_id="episode.full-collection",
                kind="collection",
                segment_index=index,
                match=match,
                claims=Claims(
                    episode=1,
                    episode_end=int(match.group(1)),
                    release_kind=ReleaseKind.COLLECTION,
                ),
                priority=95,
                specificity=3,
                evidence=("collection", "episode-range"),
            )

        for match in _EXPLICIT_EPISODE.finditer(text):
            collector.add_match(
                rule_id="episode.explicit",
                kind="episode",
                segment_index=index,
                match=match,
                claims=Claims(
                    episode=_number(match.group(1)), version=_int(match.group(2))
                ),
                priority=90,
                specificity=2,
                evidence=("episode",),
            )

        for match in _CHINESE_EPISODE.finditer(text):
            collector.add_match(
                rule_id="episode.chinese",
                kind="episode",
                segment_index=index,
                match=match,
                claims=Claims(episode=_number(match.group(1))),
                priority=90,
                specificity=2,
                evidence=("episode",),
            )

        for rule_id, pattern in (
            ("episode.pre", _PRE_EPISODE),
            ("episode.compound", _COMPOUND_EPISODE),
            ("episode.atlas", _ATLAS_EPISODE),
        ):
            special_match = pattern.match(text)
            if special_match:
                collector.add_match(
                    rule_id=rule_id,
                    kind="episode",
                    segment_index=index,
                    match=special_match,
                    claims=Claims(episode=_number(special_match.group(1))),
                    priority=75,
                    evidence=("episode",),
                )

        trailing = _TRAILING_EPISODE.search(text)
        if trailing and not _is_year_number(trailing.group(1)):
            collector.add_match(
                rule_id="episode.trailing",
                kind="episode",
                segment_index=index,
                match=trailing,
                claims=Claims(
                    episode=_number(trailing.group(1)),
                    version=_int(trailing.group(2)),
                ),
                priority=70,
                evidence=("episode",),
                conflict_tags=frozenset({"ambiguous-episode"}),
                preserve_as_title_on_conflict=True,
            )

        bare = _BARE_EPISODE.match(text)
        if bare and not _is_year_number(bare.group(1)):
            collector.add_match(
                rule_id="episode.bare",
                kind="episode",
                segment_index=index,
                match=bare,
                claims=Claims(
                    episode=_number(bare.group(1)), version=_int(bare.group(2))
                ),
                priority=70,
                evidence=("episode",),
                conflict_tags=frozenset({"ambiguous-episode"}),
                preserve_as_title_on_conflict=True,
            )


def _collect_media_candidates(collector: _CandidateCollector) -> None:
    for index, segment in enumerate(collector.segments):
        text = segment.text

        for rule_id, pattern in (
            ("media.movie-cjk", _MOVIE_CJK),
            ("media.movie-romaji", _MOVIE_ROMAJI),
        ):
            for match in pattern.finditer(text):
                collector.add_match(
                    rule_id=rule_id,
                    kind="movie",
                    segment_index=index,
                    match=match,
                    claims=Claims(media_type=MediaType.MOVIE),
                    priority=100,
                    specificity=2,
                    evidence=("movie",),
                    blocks=frozenset({"ambiguous-episode"}),
                )

        for match in _MOVIE_EN.finditer(text):
            before = text[: match.start()].rstrip()
            after = text[match.end() :].lstrip()
            marker_is_edge = not before or not after or segment.enclosure == "square"
            if re.match(r"[A-Za-z]", after):
                continue
            collector.add_match(
                rule_id="media.movie-english",
                kind="movie",
                segment_index=index,
                match=match,
                claims=Claims(media_type=MediaType.MOVIE),
                priority=100 if marker_is_edge else 99,
                specificity=2,
                evidence=("movie",),
                blocks=frozenset({"ambiguous-episode"}),
            )

        for match in _SPECIAL_WORD.finditer(text):
            after = text[match.end() :].lstrip()
            if re.match(r"[A-Za-z]", after):
                continue
            media_type = _special_media(match.group(1))
            collector.add_match(
                rule_id=f"media.{media_type.value}",
                kind="special",
                segment_index=index,
                match=match,
                claims=Claims(media_type=media_type),
                priority=80,
                specificity=1,
                evidence=(media_type.value,),
            )

        for match in _SPECIAL_CJK.finditer(text):
            collector.add_match(
                rule_id="media.special-cjk",
                kind="special",
                segment_index=index,
                match=match,
                claims=Claims(media_type=MediaType.SPECIAL),
                priority=80,
                evidence=("special",),
            )

        for match in _PV.finditer(text):
            if match.group(2) is not None:
                continue
            collector.add_match(
                rule_id="media.pv",
                kind="non-episode-video",
                segment_index=index,
                match=match,
                claims=Claims(media_type=MediaType.PV),
                priority=60,
                evidence=("pv",),
            )

        for rule_id, pattern, media_type, evidence in (
            ("media.opening", _NCOP, MediaType.OPENING, "opening"),
            ("media.ending", _NCED, MediaType.ENDING, "ending"),
        ):
            for match in pattern.finditer(text):
                collector.add_match(
                    rule_id=rule_id,
                    kind="non-episode-video",
                    segment_index=index,
                    match=match,
                    claims=Claims(media_type=media_type, version=_int(match.group(1))),
                    priority=60,
                    evidence=(evidence,),
                )

        for match in _BATCH.finditer(text):
            collector.add_match(
                rule_id="cardinality.batch",
                kind="batch",
                segment_index=index,
                match=match,
                claims=Claims(release_kind=ReleaseKind.BATCH),
                priority=80,
                evidence=("batch",),
            )

        for match in _COLLECTION.finditer(text):
            collector.add_match(
                rule_id="cardinality.collection",
                kind="collection",
                segment_index=index,
                match=match,
                claims=Claims(release_kind=ReleaseKind.COLLECTION),
                priority=80,
                evidence=("collection",),
            )


_TECHNICAL_PATTERNS = (
    _RESOLUTION,
    _SOURCE,
    _CODEC,
    _AUDIO,
    _SUBTITLE,
    _CONTAINER,
)


def _pattern_residual(text: str, patterns: tuple[re.Pattern[str], ...]) -> str:
    mask = [False] * len(text)
    for pattern in patterns:
        for match in pattern.finditer(text):
            mask[match.start() : match.end()] = [True] * (match.end() - match.start())
    return "".join(" " if used else char for char, used in zip(text, mask))


def _collect_technical_candidates(collector: _CandidateCollector) -> None:
    for index, segment in enumerate(collector.segments):
        text = segment.text

        for match in _RESOLUTION.finditer(text):
            collector.add_match(
                rule_id="technical.resolution",
                kind="resolution",
                segment_index=index,
                match=match,
                claims=Claims(resolution=match.group()),
                priority=30,
                evidence=("resolution",),
            )

        for match in _SOURCE.finditer(text):
            collector.add_match(
                rule_id="technical.source",
                kind="source",
                segment_index=index,
                match=match,
                claims=Claims(source=match.group()),
                priority=30,
                evidence=("source",),
            )

        for match in _CODEC.finditer(text):
            collector.add_match(
                rule_id="technical.codec",
                kind="codec",
                segment_index=index,
                match=match,
                claims=Claims(codecs=(match.group(),)),
                priority=30,
            )

        for match in _AUDIO.finditer(text):
            collector.add_match(
                rule_id="technical.audio",
                kind="audio",
                segment_index=index,
                match=match,
                claims=Claims(audio=(match.group(),)),
                priority=30,
            )

        for match in _SUBTITLE.finditer(text):
            container_match = re.search(r"_(MP4|MKV)$", match.group(), re.I)
            collector.add_match(
                rule_id="technical.subtitle",
                kind="subtitle",
                segment_index=index,
                match=match,
                claims=Claims(
                    subtitle=re.sub(r"_(?:MP4|MKV)$", "", match.group(), flags=re.I),
                    container=(container_match.group(1) if container_match else None),
                ),
                priority=35 if container_match else 30,
                specificity=2 if container_match else 1,
            )

        for match in _CONTAINER.finditer(text):
            collector.add_match(
                rule_id="technical.container",
                kind="container",
                segment_index=index,
                match=match,
                claims=Claims(container=match.group(1)),
                priority=30,
            )

        if segment.enclosure == "square":
            residual = _clean_fragment(_pattern_residual(text, _TECHNICAL_PATTERNS))
            if residual and _CJK_SUBTITLE_TAG.fullmatch(residual):
                collector.add_span(
                    rule_id="technical.subtitle-cjk",
                    kind="subtitle",
                    segment_index=index,
                    start=0,
                    end=len(text),
                    claims=Claims(subtitle=residual),
                    priority=45,
                    evidence=(),
                    overlap_policy=OverlapPolicy.SHARED,
                )
            if _DUB.search(text):
                collector.add_span(
                    rule_id="metadata.dub",
                    kind="tag",
                    segment_index=index,
                    start=0,
                    end=len(text),
                    claims=Claims(tags=(text.strip(),)),
                    priority=45,
                    overlap_policy=OverlapPolicy.SHARED,
                )

        for match in _VERSION.finditer(text):
            collector.add_match(
                rule_id="metadata.version",
                kind="version",
                segment_index=index,
                match=match,
                claims=Claims(version=int(match.group(1))),
                priority=20,
            )

        for rule_id, pattern in (
            ("metadata.prefix", _PREFIX),
            ("metadata.recruitment", _RECRUIT),
            ("metadata.region", _REGION),
            ("metadata.trailing-group", _TRAILING_RELEASE_GROUP),
        ):
            for match in pattern.finditer(text):
                collector.add_match(
                    rule_id=rule_id,
                    kind="tag",
                    segment_index=index,
                    match=match,
                    claims=Claims(tags=(match.group().strip(),)),
                    priority=25,
                )

        for match in _HASH.finditer(text):
            collector.add_match(
                rule_id="metadata.hash",
                kind="tag",
                segment_index=index,
                match=match,
                claims=Claims(tags=(match.group(),)),
                priority=25,
            )

        if segment.enclosure in {"square", "round"}:
            residual = _clean_fragment(_pattern_residual(text, _TECHNICAL_PATTERNS))
            if residual.lower() in {"end", "生"}:
                collector.add_span(
                    rule_id="metadata.end-marker",
                    kind="tag",
                    segment_index=index,
                    start=0,
                    end=len(text),
                    claims=Claims(tags=(residual,)),
                    priority=25,
                    overlap_policy=OverlapPolicy.SHARED,
                )


def _collect_metadata_episode_candidates(collector: _CandidateCollector) -> None:
    for index, segment in enumerate(collector.segments):
        if segment.enclosure != "square":
            continue
        residual = _pattern_residual(segment.text, _TECHNICAL_PATTERNS)
        episode_match = _BARE_EPISODE.match(residual) or _TRAILING_EPISODE.search(
            residual
        )
        if not episode_match or _is_year_number(episode_match.group(1)):
            continue
        start = episode_match.start(1)
        end = (
            episode_match.end(2)
            if episode_match.group(2) is not None
            else episode_match.end(1)
        )
        collector.add_span(
            rule_id="episode.metadata-mixed",
            kind="episode",
            segment_index=index,
            start=start,
            end=end,
            claims=Claims(
                episode=_number(episode_match.group(1)),
                version=_int(episode_match.group(2)),
            ),
            priority=65,
            evidence=("episode",),
            conflict_tags=frozenset({"ambiguous-episode"}),
            preserve_as_title_on_conflict=True,
            captures=episode_match.groups(),
        )


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


def _reconstruct_titles(
    working: list[_ResidualSegment],
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
