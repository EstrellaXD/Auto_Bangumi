import re

from .keywords import CJK_SUBWORDS, KEYWORDS, PATTERN_CHECKS
from .token import Token, TokenKind

_SUB_TOKEN_DELIM = re.compile(r"\s+")


def classify(tokens: list[Token]) -> list[Token]:
    result: list[Token] = []
    for token in tokens:
        classified = _classify_token(token)
        if classified.kind != TokenKind.UNKNOWN:
            result.append(classified)
            continue

        # Split whitespace compounds before scanning the whole token for a CJK
        # marker.  Otherwise "Tenki no Ko 剧场版" becomes one MOVIE token and
        # the English title is discarded with the marker.
        sub_tokens = _try_split_compound(classified)
        if len(sub_tokens) > 1:
            result.extend(sub_tokens)
            continue

        if _try_cjk_subword(classified):
            result.append(classified)
            continue

        result.append(classified)
    return result


def _classify_token(token: Token) -> Token:
    lower = token.text.lower()

    if lower in KEYWORDS:
        token.kind = KEYWORDS[lower]
        return token

    for pattern, kind in PATTERN_CHECKS:
        if pattern.match(token.text):
            token.kind = kind
            return token

    return token


def _try_cjk_subword(token: Token) -> bool:
    """Scan CJK-dominant tokens for known sub-words. Longest match wins."""
    text = token.text
    if not any("\u4e00" <= c <= "\u9fff" or "\u3400" <= c <= "\u4dbf" for c in text):
        return False
    best_kind = None
    best_len = 0
    for subword, kind in CJK_SUBWORDS.items():
        if subword in text and len(subword) > best_len:
            best_kind = kind
            best_len = len(subword)
    if best_kind:
        token.kind = best_kind
        return True
    return False


def _try_split_compound(token: Token) -> list[Token]:
    """Split compound tokens like 'WebRip 1080p HEVC-10bit AAC' or
    '天国大魔境 Tengoku Daimakyou 第05话 GB 720P MP4'."""
    parts = _SUB_TOKEN_DELIM.split(token.text)
    if len(parts) <= 1:
        return [token]

    classified_parts: list[Token] = []
    unknown_parts: list[str] = []

    for part in parts:
        sub = Token(
            text=part,
            kind=TokenKind.UNKNOWN,
            position=token.position,
            enclosed=token.enclosed,
        )
        sub = _classify_token(sub)
        if sub.kind == TokenKind.UNKNOWN:
            _try_cjk_subword(sub)
        if sub.kind != TokenKind.UNKNOWN:
            if unknown_parts:
                merged = " ".join(unknown_parts)
                classified_parts.append(
                    Token(
                        text=merged,
                        kind=TokenKind.UNKNOWN,
                        position=token.position,
                        enclosed=token.enclosed,
                    )
                )
                unknown_parts = []
            classified_parts.append(sub)
        else:
            unknown_parts.append(part)

    if unknown_parts:
        merged = " ".join(unknown_parts)
        classified_parts.append(
            Token(
                text=merged,
                kind=TokenKind.UNKNOWN,
                position=token.position,
                enclosed=token.enclosed,
            )
        )

    if any(t.kind != TokenKind.UNKNOWN for t in classified_parts):
        return classified_parts
    return [token]
