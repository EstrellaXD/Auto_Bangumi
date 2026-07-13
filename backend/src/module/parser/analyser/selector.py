"""Select the configured deterministic resource-title parser."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Literal, cast

from module.conf import settings

from .tokenizer import classic
from .tokenizer import parser as preview
from .tokenizer.result import ParsedRelease
from .tokenizer.trace import ParseTrace

ParserEngine = Literal["classic", "tokenizer"]

_PARSER_ENGINE_SNAPSHOT: ContextVar[ParserEngine | None] = ContextVar(
    "parser_engine_snapshot",
    default=None,
)


@dataclass(frozen=True, slots=True)
class ConfiguredParseOutcome:
    """A configured parse result with diagnostics when the engine supports them."""

    engine: ParserEngine
    result: ParsedRelease | None
    trace: ParseTrace | None = None


@contextmanager
def parser_engine_snapshot() -> Iterator[ParserEngine]:
    """Keep one configured engine for all parses in the current task scope.

    ``ContextVar`` state survives ``await`` boundaries, is copied into child
    tasks, and remains isolated from unrelated concurrent tasks. Nested scopes
    reuse the already-bound engine instead of observing a mid-workflow reload.
    """
    engine = _configured_engine()
    token = _PARSER_ENGINE_SNAPSHOT.set(engine)
    try:
        yield engine
    finally:
        _PARSER_ENGINE_SNAPSHOT.reset(token)


def parse_configured_release_title(raw: str) -> ParsedRelease | None:
    """Parse *raw* with the engine selected for this invocation."""
    return parse_configured_release_title_outcome(raw).result


def parse_configured_release_title_outcome(raw: str) -> ConfiguredParseOutcome:
    """Parse *raw* and retain the engine selected for this invocation."""
    engine = _configured_engine()
    if engine == "classic":
        result = classic.parse_release_title(raw)
    else:
        result = preview.parse_release_title(raw)
    return ConfiguredParseOutcome(engine=engine, result=result)


def parse_configured_release_title_with_trace(raw: str) -> ConfiguredParseOutcome:
    """Parse *raw* and include the Preview engine's native trace when available."""
    engine = _configured_engine()
    if engine == "classic":
        return ConfiguredParseOutcome(
            engine=engine,
            result=classic.parse_release_title(raw),
        )

    outcome = preview.parse_release_title_with_trace(raw)
    return ConfiguredParseOutcome(
        engine=engine,
        result=outcome.result,
        trace=outcome.trace,
    )


def _configured_engine() -> ParserEngine:
    snapshot = _PARSER_ENGINE_SNAPSHOT.get()
    if snapshot is not None:
        return snapshot

    # Older in-memory Settings instances can predate the field during a live
    # reload.  Missing means the documented stable default; invalid values are
    # never silently corrected here.
    engine = getattr(settings.rss_parser, "engine", "classic")
    if engine not in {"classic", "tokenizer"}:
        raise ValueError(f"Unsupported RSS parser engine: {engine!r}")
    return cast(ParserEngine, engine)
