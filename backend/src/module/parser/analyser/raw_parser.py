import logging

from module.models import Episode
from module.parser.analyser.tokenizer import parse_release_title, tokenize_title
from module.parser.analyser.tokenizer.compat import legacy_non_episodic_type

logger = logging.getLogger(__name__)


def get_group(raw: str) -> str:
    """Return the first square-bracket group, or an empty string."""
    parsed = parse_release_title(raw)
    return parsed.group if parsed and parsed.group else ""


def _detect_non_episodic_type(raw: str) -> str | None:
    """Classify movie/special markers for LLM results.

    The tokenizer performs the normal deterministic classification.  This
    helper remains the compatibility seam used by ``TitleParser`` when an LLM
    result needs its episode type corrected from the original release title.
    """
    parsed = parse_release_title(raw)
    if parsed is None:
        return None
    return legacy_non_episodic_type(parsed.media_type)


def raw_parser(raw: str) -> Episode | None:
    result = tokenize_title(raw)
    if result is None:
        logger.info("Cannot parse resource: %s, skipping.", raw)
    return result
