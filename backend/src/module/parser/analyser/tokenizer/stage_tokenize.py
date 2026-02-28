import re

from .token import Token, TokenKind

# Only square and ASCII round brackets are structural delimiters
# Full-width （） are treated as regular text (they're CJK punctuation in titles)
_OPEN_BRACKETS = {"[": "]", "(": ")"}
_CLOSE_BRACKETS = {"]", ")"}
_FREE_DELIMITERS = re.compile(r"\s+-\s+|/|\s{2,}")
_ENCLOSED_DELIMITERS = re.compile(r"/")


def _add_parts(
    text: str, pos: int, enclosed: bool, delim: re.Pattern, tokens: list[Token]
) -> int:
    parts = delim.split(text)
    for part in parts:
        part = part.strip()
        if part:
            tokens.append(
                Token(
                    text=part, kind=TokenKind.UNKNOWN, position=pos, enclosed=enclosed
                )
            )
            pos += 1
    return pos


def tokenize(normalized: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    i = 0
    n = len(normalized)

    while i < n:
        ch = normalized[i]

        if ch in _OPEN_BRACKETS:
            close = _OPEN_BRACKETS[ch]
            j = normalized.find(close, i + 1)
            if j == -1:
                j = n
            inner = normalized[i + 1 : j].strip()
            if inner:
                pos = _add_parts(inner, pos, True, _ENCLOSED_DELIMITERS, tokens)
            i = j + 1

        elif ch in _CLOSE_BRACKETS:
            i += 1

        else:
            j = i
            while (
                j < n
                and normalized[j] not in _OPEN_BRACKETS
                and normalized[j] not in _CLOSE_BRACKETS
            ):
                j += 1
            free = normalized[i:j].strip()
            if free:
                pos = _add_parts(free, pos, False, _FREE_DELIMITERS, tokens)
            i = j

    return tokens
