import logging
import re

from module.models import Episode
from module.parser.analyser.tokenizer import tokenize_title

logger = logging.getLogger(__name__)


_MOVIE_TOKEN_RE = re.compile(
    r"剧场版|劇場版|电影版|電影版|\bmovie\b|\bgekijou-?ban\b",
    re.IGNORECASE,
)
_SPECIAL_TOKEN_RE = re.compile(
    r"\bOVA\d*\b|\bOAD\d*\b|\bSP\d*\b|\bspecial\b|番外篇?|特别篇|特別篇",
    re.IGNORECASE,
)
_LEADING_GROUP_RE = re.compile(r"^\s*[\[【][^\]】]+[\]】]\s*")
_GROUP_RE = re.compile(r"\[([^\]]*)\]")


def get_group(raw: str) -> str:
    """Return the first square-bracket group, or an empty string."""
    match = _GROUP_RE.search(raw)
    return match.group(1) if match else ""


def _detect_non_episodic_type(raw: str) -> str | None:
    """Classify movie/special markers for LLM results.

    The tokenizer performs the normal deterministic classification.  This
    helper remains the compatibility seam used by ``TitleParser`` when an LLM
    result needs its episode type corrected from the original release title.
    """
    content = _LEADING_GROUP_RE.sub("", raw, count=1)
    if _MOVIE_TOKEN_RE.search(content):
        return "movie"
    if _SPECIAL_TOKEN_RE.search(content):
        return "special"
    return None


def raw_parser(raw: str) -> Episode | None:
    result = tokenize_title(raw)
    if result is None:
        logger.info("Cannot parse resource: %s, skipping.", raw)
    return result
