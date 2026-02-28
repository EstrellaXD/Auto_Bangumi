"""Hot-reload keyword dictionaries from a remote JSON file.

Periodically fetches ``keywords_extra.json`` from the repo's main branch
and merges new entries into the in-memory KEYWORDS / CJK_SUBWORDS dicts.
Built-in keywords always take precedence — remote entries only add, never override.
"""

import json
import logging
import time
import urllib.request

from .token import TokenKind

logger = logging.getLogger(__name__)

DEFAULT_URL = (
    "https://raw.githubusercontent.com/EstrellaXD/Auto_Bangumi/"
    "main/backend/src/module/parser/analyser/tokenizer/keywords_extra.json"
)

RELOAD_INTERVAL = 3600  # seconds

_last_fetch: float = 0.0
_remote_version: int = 0


def maybe_reload() -> None:
    """Fetch remote keywords if the reload interval has elapsed. Never raises."""
    global _last_fetch, _remote_version

    now = time.time()
    if now - _last_fetch < RELOAD_INTERVAL:
        return

    try:
        req = urllib.request.Request(
            DEFAULT_URL, headers={"User-Agent": "AutoBangumi-HotReload/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())

        version = data.get("version", 0)
        if version <= _remote_version:
            _last_fetch = now
            return  # already up to date

        _merge(data)
        _remote_version = version
        _last_fetch = now
        logger.info(f"Hot-reloaded keywords v{version}")

    except Exception:
        # Retry after interval, not immediately
        _last_fetch = now
        logger.debug("Failed to fetch remote keywords, will retry later")


def _merge(data: dict) -> None:
    """Merge remote entries into keyword dicts. Remote never overrides built-in."""
    from .keywords import CJK_SUBWORDS, KEYWORDS

    added = 0

    for k, v in data.get("keywords", {}).items():
        key = k.lower()
        if key not in KEYWORDS:
            try:
                KEYWORDS[key] = TokenKind[v]
                added += 1
            except KeyError:
                logger.warning(f"Unknown TokenKind '{v}' for keyword '{k}', skipping")

    for k, v in data.get("cjk_subwords", {}).items():
        if k not in CJK_SUBWORDS:
            try:
                CJK_SUBWORDS[k] = TokenKind[v]
                added += 1
            except KeyError:
                logger.warning(
                    f"Unknown TokenKind '{v}' for CJK subword '{k}', skipping"
                )

    # prefix_tags are stored as KEYWORDS entries with PREFIX_TAG kind
    for tag in data.get("prefix_tags", []):
        if tag not in KEYWORDS:
            KEYWORDS[tag] = TokenKind.PREFIX_TAG
            added += 1

    if added:
        logger.info(f"Merged {added} new keyword(s) from remote")
