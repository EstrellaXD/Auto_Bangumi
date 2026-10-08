import logging

from module.models import Episode
from module.parser.analyser.selector import parse_configured_release_title
from module.parser.analyser.tokenizer.compat import (
    to_legacy_episode,
)

logger = logging.getLogger(__name__)


def get_group(raw: str) -> str:
    """Return the first square-bracket group, or an empty string."""
    parsed = parse_configured_release_title(raw)
    return parsed.group if parsed and parsed.group else ""


def raw_parser(raw: str) -> Episode | None:
    parsed = parse_configured_release_title(raw)
    result = to_legacy_episode(parsed) if parsed is not None else None
    if result is None:
        logger.info("Cannot parse resource: %s, skipping.", raw)
    return result
