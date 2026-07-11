"""Input normalization shared by the release-title parser."""

from __future__ import annotations

import re

_FILE_EXTENSION = re.compile(r"\.(mp4|mkv|avi|ass|srt|ssa|sub)$", re.I)


def normalize(raw: str) -> str:
    value = raw.strip().replace("\n", " ")
    value = value.replace("【", "[").replace("】", "]")
    # Full-width slashes and parentheses are title punctuation, not structure.
    return _FILE_EXTENSION.sub("", value)
