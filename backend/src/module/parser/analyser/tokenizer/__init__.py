from module.models import Episode

from . import hot_reload
from .stage_classify import classify
from .stage_compose import compose
from .stage_normalize import normalize
from .stage_resolve import resolve
from .stage_tokenize import tokenize


def tokenize_title(raw: str) -> Episode | None:
    hot_reload.maybe_reload()
    normalized = normalize(raw)
    tokens = tokenize(normalized)
    if not tokens:
        return None
    tokens = classify(tokens)
    tokens = resolve(tokens)
    return compose(tokens)
