import asyncio
from types import SimpleNamespace

import pytest

from module.parser.analyser import selector
from module.parser.analyser.raw_parser import raw_parser
from module.parser.analyser.selector import (
    ConfiguredParseOutcome,
    parse_configured_release_title,
    parse_configured_release_title_with_trace,
    parser_engine_snapshot,
)
from module.parser.analyser.tokenizer import MediaType, ReleaseKind
from module.parser.analyser.tokenizer.classic import (
    parse_release_title as parse_classic_release_title,
)
from module.parser.analyser.tokenizer.result import ParsedRelease
from module.parser.analyser.tokenizer.trace import ParseOutcome, ParseTrace


def _use_engine(monkeypatch: pytest.MonkeyPatch, engine: str) -> None:
    monkeypatch.setattr(
        selector,
        "settings",
        SimpleNamespace(rss_parser=SimpleNamespace(engine=engine)),
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "[Group] Anime Season 2 Episode 03 [1080p]",
            {
                "title_en": "Anime",
                "season": 2,
                "episode": 3,
                "media_type": MediaType.EPISODE,
            },
        ),
        (
            "[Group] 劇場版 86 - 0 [1080p WEB-DL]",
            {
                "title_en": "86 - 0",
                "episode": None,
                "media_type": MediaType.MOVIE,
            },
        ),
        (
            "[Group] Anime OVA 01 [1080p]",
            {
                "title_en": "Anime",
                "episode": 1,
                "media_type": MediaType.OVA,
            },
        ),
        (
            "[Group] 86 - 12 [1080p]",
            {
                "title_en": "86",
                "episode": 12,
                "media_type": MediaType.EPISODE,
            },
        ),
    ],
)
def test_classic_parser_frozen_regressions(
    raw: str, expected: dict[str, object]
) -> None:
    parsed = parse_classic_release_title(raw)

    assert parsed is not None
    for field, value in expected.items():
        assert getattr(parsed, field) == value


def test_classic_and_preview_are_distinct_implementations() -> None:
    raw = "[Group] Anime EP01 ~ EP02 [1080p]"

    classic = parse_classic_release_title(raw)
    preview = selector.preview.parse_release_title(raw)

    assert classic is not None
    assert preview is not None
    assert (classic.episode, classic.episode_end, classic.release_kind) == (
        2,
        None,
        ReleaseKind.SINGLE,
    )
    assert (preview.episode, preview.episode_end, preview.release_kind) == (
        1,
        2,
        ReleaseKind.RANGE,
    )


@pytest.mark.parametrize(
    "parse",
    [parse_classic_release_title, selector.preview.parse_release_title],
    ids=["classic", "preview"],
)
@pytest.mark.parametrize("title", ["某剧场作品", "小剧场", "某劇場作品", "小劇場"])
def test_cjk_movie_word_inside_title_is_not_consumed(parse, title: str) -> None:
    parsed = parse(f"[SubGroup] {title} Movie [1080p][MP4]")

    assert parsed is not None
    assert parsed.title_zh == title
    assert parsed.media_type is MediaType.MOVIE


@pytest.mark.parametrize(
    "parse",
    [parse_classic_release_title, selector.preview.parse_release_title],
    ids=["classic", "preview"],
)
def test_standalone_cjk_movie_marker_is_still_consumed(parse) -> None:
    parsed = parse("[SubGroup] 某动画 / Some Anime 剧场 [1080p][MP4]")

    assert parsed is not None
    assert parsed.title_zh == "某动画"
    assert parsed.title_en == "Some Anime"
    assert parsed.media_type is MediaType.MOVIE


def test_selector_uses_classic_without_preview_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_engine(monkeypatch, "classic")
    expected = ParsedRelease(raw="classic", title_en="Classic")
    monkeypatch.setattr(selector.classic, "parse_release_title", lambda raw: expected)

    def fail_preview(raw: str) -> ParsedRelease | None:
        pytest.fail("Preview parser must not run in Classic mode")

    monkeypatch.setattr(selector.preview, "parse_release_title", fail_preview)

    assert parse_configured_release_title("resource") is expected


def test_selector_returns_native_preview_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_engine(monkeypatch, "tokenizer")
    expected = ParsedRelease(raw="preview", title_en="Preview")
    trace = ParseTrace(raw="resource", normalized="resource")
    monkeypatch.setattr(
        selector.preview,
        "parse_release_title_with_trace",
        lambda raw: ParseOutcome(result=expected, trace=trace),
    )

    outcome = parse_configured_release_title_with_trace("resource")

    assert outcome == ConfiguredParseOutcome(
        engine="tokenizer",
        result=expected,
        trace=trace,
    )


def test_selector_classic_trace_is_explicitly_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_engine(monkeypatch, "classic")
    expected = ParsedRelease(raw="classic", title_en="Classic")
    monkeypatch.setattr(selector.classic, "parse_release_title", lambda raw: expected)

    outcome = parse_configured_release_title_with_trace("resource")

    assert outcome == ConfiguredParseOutcome(
        engine="classic",
        result=expected,
        trace=None,
    )


def test_preview_failure_never_invokes_classic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_engine(monkeypatch, "tokenizer")
    monkeypatch.setattr(selector.preview, "parse_release_title", lambda raw: None)

    def fail_classic(raw: str) -> ParsedRelease | None:
        pytest.fail("Classic parser must not be a Preview fallback")

    monkeypatch.setattr(selector.classic, "parse_release_title", fail_classic)

    assert parse_configured_release_title("resource") is None


def test_selector_reads_engine_once_per_parse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CountingRSSParser:
        reads = 0

        @property
        def engine(self) -> str:
            self.reads += 1
            return "classic"

    rss_parser = CountingRSSParser()
    monkeypatch.setattr(
        selector,
        "settings",
        SimpleNamespace(rss_parser=rss_parser),
    )
    monkeypatch.setattr(selector.classic, "parse_release_title", lambda raw: None)

    parse_configured_release_title("resource")

    assert rss_parser.reads == 1


async def test_parser_engine_snapshot_is_isolated_to_its_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parser_config = SimpleNamespace(engine="classic")
    monkeypatch.setattr(
        selector,
        "settings",
        SimpleNamespace(rss_parser=parser_config),
    )
    classic = ParsedRelease(raw="classic", title_en="Classic")
    preview = ParsedRelease(raw="preview", title_en="Preview")
    monkeypatch.setattr(selector.classic, "parse_release_title", lambda raw: classic)
    monkeypatch.setattr(selector.preview, "parse_release_title", lambda raw: preview)

    setting_changed = asyncio.Event()
    unscoped_finished = asyncio.Event()

    async def scoped_parse() -> ParsedRelease | None:
        with parser_engine_snapshot():
            parser_config.engine = "tokenizer"
            setting_changed.set()
            await unscoped_finished.wait()
            return parse_configured_release_title("resource")

    async def unscoped_parse() -> ParsedRelease | None:
        await setting_changed.wait()
        result = parse_configured_release_title("resource")
        unscoped_finished.set()
        return result

    scoped, unscoped = await asyncio.gather(scoped_parse(), unscoped_parse())

    assert scoped is classic
    assert unscoped is preview


def test_missing_engine_uses_stable_classic_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        selector,
        "settings",
        SimpleNamespace(rss_parser=SimpleNamespace()),
    )
    expected = ParsedRelease(raw="classic", title_en="Classic")
    monkeypatch.setattr(selector.classic, "parse_release_title", lambda raw: expected)

    assert parse_configured_release_title("resource") is expected


def test_invalid_runtime_engine_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_engine(monkeypatch, "invalid")

    with pytest.raises(ValueError, match="Unsupported RSS parser engine"):
        parse_configured_release_title("resource")


def test_legacy_episode_compatibility_entry_follows_selected_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = "[Group] Anime EP01 ~ EP02 [1080p]"

    _use_engine(monkeypatch, "classic")
    classic = raw_parser(raw)
    _use_engine(monkeypatch, "tokenizer")
    preview = raw_parser(raw)

    assert classic is not None
    assert classic.episode == 2
    assert preview is None
