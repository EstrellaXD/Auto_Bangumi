import re

from .token import Token, TokenKind

_CJK_HAN = re.compile(r"[\u4e00-\u9fff]")
_CJK_TRAD = re.compile(r"[\u3400-\u4dbf\uf900-\ufaff]")
_KATAKANA_HIRAGANA = re.compile(r"[\u3040-\u309f\u30a0-\u30ff]")
_LATIN = re.compile(r"[a-zA-Z]")
_PURE_DIGITS = re.compile(r"^\d{1,4}$")
_PRE_EP = re.compile(r"^(\d+)[Pp]re$")
_COMPOUND_EP = re.compile(r"^(\d+)\(\d+\)$")
_SE_COMBINED = re.compile(r"^[Ss](\d{1,2})[Ee](\d+)$")
_ATLAS_EP = re.compile(r"^(\d+)_(.+)$")
_SEASON_EMBEDDED = re.compile(r"^(.*?)\s*第([一二三四五六七八九十\d]+)[季期]$")
_NUM_PREFIX_CJK = re.compile(r"^(\d+)\s+([\u4e00-\u9fff].*)$")
_PREFIX_TAG_RE = re.compile(r"^\d+月新番$|^新番$|^★.*★$")
_PREFIX_STRIP_RE = re.compile(r"^★?\d*月?新番\s*|^★\d+月新番★?\s*")
_REGION_RE = re.compile(r"[(（](?:仅限)?港澳台地区[）)]")
_RECRUIT_RE = re.compile(
    r"[(（]?(?:字幕社?)?招[募人].*[）)]?$|急招翻校轴|搜索用[：:].*$"
)

# Episode suffixed to title: "title-01", "title - 08"
_TRAILING_EP = re.compile(r"^(.*?)\s*-\s*(\d{1,4})\s*$")
# Episode at end of free text: "title 03" (digits after space, before brackets)
_TRAILING_DIGITS = re.compile(r"^(.*\S)\s+(\d{1,4})\s*$")

_TITLE_UNDERSCORE_SPLIT = re.compile(r"_")
_YEAR_RANGE = range(1990, 2031)
_TRAILING_PART = re.compile(r"\bPart\s*$", re.I)
_PURE_HAN_WORD = re.compile(r"^[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+$")


def _has_cjk(text: str) -> bool:
    return bool(_CJK_HAN.search(text) or _CJK_TRAD.search(text))


def _has_jp(text: str) -> bool:
    return bool(_KATAKANA_HIRAGANA.search(text))


def _has_latin(text: str) -> bool:
    return bool(_LATIN.search(text))


def _classify_title_lang(text: str) -> TokenKind:
    if _has_jp(text):
        return TokenKind.TITLE_JP
    if _has_cjk(text):
        return TokenKind.TITLE_ZH
    if _has_latin(text):
        return TokenKind.TITLE_EN
    return TokenKind.TITLE_EN


def _split_word_at_cjk_boundary(word: str) -> list[str]:
    """Split a single word at the boundary between Latin and CJK characters.

    E.g. 'MOON：月之神坛' → ['MOON：', '月之神坛']
    Only splits if the word has both Latin and CJK characters.
    """
    if not (_has_latin(word) and (_has_cjk(word) or _has_jp(word))):
        return [word]
    # Find the first CJK character position
    for i, ch in enumerate(word):
        if _CJK_HAN.match(ch) or _CJK_TRAD.match(ch) or _KATAKANA_HIRAGANA.match(ch):
            left = word[:i].rstrip("：:·・")
            right = word[i:]
            if left and right:
                return [left, right]
            break
    return [word]


def _split_mixed_title(text: str) -> list[str]:
    """Split a mixed CJK/Latin title into language segments."""
    if "_" in text:
        parts = _TITLE_UNDERSCORE_SPLIT.split(text, 1)
        if len(parts) == 2:
            p1, p2 = parts[0].strip(), parts[1].strip()
            if p1 and p2 and _has_cjk(p1) != _has_cjk(p2):
                return [p1, p2]
            if p1 and p2 and _has_cjk(p1) and _has_cjk(p2):
                return [p1, p2]

    words = text.split(" ")
    if len(words) < 2:
        # Single word — try splitting at CJK boundary within the word
        return _split_word_at_cjk_boundary(text)

    # Some release names concatenate Chinese, Japanese and English titles
    # without slash separators, for example:
    #   想星的阿克艾利昂 情感神话 想星のアクエリオン Aquarion: Myth...
    # Preserve the leading Chinese title instead of folding it into the first
    # kana-containing block (which would classify the whole block as JP).
    if _PURE_HAN_WORD.match(words[0]):
        jp_idx = next((i for i, word in enumerate(words[1:], 1) if _has_jp(word)), None)
        if jp_idx is not None:
            en_idx = next(
                (
                    i
                    for i, word in enumerate(words[jp_idx + 1 :], jp_idx + 1)
                    if _has_latin(word) and not _has_cjk(word) and not _has_jp(word)
                ),
                None,
            )
            if en_idx is not None:
                middle = " ".join(words[1:en_idx]).strip()
                english = " ".join(words[en_idx:]).strip()
                if middle and english:
                    return [words[0], middle, english]

    # Pre-split words that contain both CJK and Latin at their boundary
    expanded: list[str] = []
    for word in words:
        expanded.extend(_split_word_at_cjk_boundary(word))

    # Classify each fragment as CJK or Latin
    groups: list[tuple[str, str]] = []
    for frag in expanded:
        if (
            _CJK_HAN.search(frag)
            or _CJK_TRAD.search(frag)
            or _KATAKANA_HIRAGANA.search(frag)
        ):
            groups.append(("cjk", frag))
        else:
            groups.append(("lat", frag))

    # Only split if there's exactly one language transition
    # (CJK block → Latin block or vice versa, no interleaving)
    transitions = sum(
        1 for i in range(1, len(groups)) if groups[i][0] != groups[i - 1][0]
    )
    if transitions != 1:
        return [text]

    first_lang = groups[0][0]
    split_idx = next(i for i in range(1, len(groups)) if groups[i][0] != first_lang)

    part1 = " ".join(w for _, w in groups[:split_idx])
    part2 = " ".join(w for _, w in groups[split_idx:])

    if not part1 or not part2:
        return [text]

    return [part1, part2]


_STANDALONE_JUNK = re.compile(r"^[-—–\s]+$")


def resolve(tokens: list[Token]) -> list[Token]:
    _filter_junk_tokens(tokens)
    _resolve_se_combined(tokens)
    _resolve_pre_episodes(tokens)
    _resolve_compound_episodes(tokens)
    _resolve_atlas_episodes(tokens)
    _resolve_trailing_episodes(tokens)
    _resolve_bare_episode(tokens)
    _resolve_group(tokens)
    _resolve_prefix_tags(tokens)
    _resolve_region_recruit(tokens)
    _split_mixed_language_tokens(tokens)
    _resolve_titles(tokens)
    return tokens


def _filter_junk_tokens(tokens: list[Token]) -> None:
    """Mark standalone dashes and whitespace-only tokens as EXTRA.
    Also strip trailing dash-space from tokens (Doomdos format artifacts)."""
    for token in tokens:
        if token.kind != TokenKind.UNKNOWN:
            continue
        if _STANDALONE_JUNK.match(token.text):
            token.kind = TokenKind.EXTRA
            continue
        # Strip leading/trailing separator dashes (space-dash or dash-space)
        cleaned = re.sub(r"^\s*-\s+|\s+-\s*$", "", token.text).strip()
        if cleaned and cleaned != token.text:
            token.text = cleaned


def _resolve_se_combined(tokens: list[Token]) -> None:
    for token in tokens:
        if token.kind == TokenKind.EPISODE:
            m = _SE_COMBINED.match(token.text)
            if m:
                token.text = m.group(2)
                season_tok = Token(
                    text=f"S{m.group(1)}",
                    kind=TokenKind.SEASON,
                    position=token.position,
                    enclosed=token.enclosed,
                )
                idx = tokens.index(token)
                tokens.insert(idx, season_tok)


def _resolve_pre_episodes(tokens: list[Token]) -> None:
    for token in tokens:
        if token.kind != TokenKind.UNKNOWN:
            continue
        m = _PRE_EP.match(token.text)
        if m:
            token.kind = TokenKind.EPISODE
            token.text = m.group(1)


def _resolve_compound_episodes(tokens: list[Token]) -> None:
    for token in tokens:
        if token.kind != TokenKind.UNKNOWN:
            continue
        m = _COMPOUND_EP.match(token.text)
        if m:
            token.kind = TokenKind.EPISODE
            token.text = m.group(1)


def _resolve_atlas_episodes(tokens: list[Token]) -> None:
    for token in tokens:
        if token.kind != TokenKind.UNKNOWN:
            continue
        m = _ATLAS_EP.match(token.text)
        if m and m.group(2) and _has_cjk(m.group(2)):
            token.kind = TokenKind.EPISODE
            token.text = m.group(1)


def _resolve_trailing_episodes(tokens: list[Token]) -> None:
    """Extract episode numbers from the end of UNKNOWN tokens.

    Handles:
    - 'title-01' or 'title - 08' (dash-separated)
    - 'title 03' (space-separated, only when no episode found yet)
    """
    episodes_found = any(t.kind == TokenKind.EPISODE for t in tokens)
    if episodes_found:
        return

    for i, token in enumerate(tokens):
        if token.kind != TokenKind.UNKNOWN:
            continue

        # Try dash-separated episode: "title-01"
        m = _TRAILING_EP.match(token.text)
        if m and m.group(1).strip():
            title_part = m.group(1).strip()
            ep_text = m.group(2)
            # Don't extract if the "title" part is just digits or very short
            if _has_cjk(title_part) or _has_latin(title_part):
                token.text = title_part
                ep_tok = Token(
                    text=ep_text,
                    kind=TokenKind.EPISODE,
                    position=token.position,
                    enclosed=token.enclosed,
                )
                tokens.insert(i + 1, ep_tok)
                return

        # Try trailing digits: "title 03"
        m = _TRAILING_DIGITS.match(token.text)
        if m and m.group(1).strip():
            title_part = m.group(1).strip()
            ep_text = m.group(2)
            if _is_year(ep_text):
                continue
            # Skip "Part 2", "Part2" patterns
            if _TRAILING_PART.search(title_part):
                continue
            # Only if the title part has meaningful content
            if (
                _has_cjk(title_part) or _has_latin(title_part)
            ) and not _PURE_DIGITS.match(title_part):
                token.text = title_part
                ep_tok = Token(
                    text=ep_text,
                    kind=TokenKind.EPISODE,
                    position=token.position,
                    enclosed=token.enclosed,
                )
                tokens.insert(i + 1, ep_tok)
                return


def _is_year(text: str) -> bool:
    """Check if a pure-digit string looks like a year (1990-2030)."""
    if len(text) != 4:
        return False
    try:
        return int(text) in _YEAR_RANGE
    except ValueError:
        return False


def _resolve_bare_episode(tokens: list[Token]) -> None:
    episodes_found = any(t.kind == TokenKind.EPISODE for t in tokens)
    if episodes_found:
        return

    unknowns = [t for t in tokens if t.kind == TokenKind.UNKNOWN]
    for token in unknowns:
        if not _PURE_DIGITS.match(token.text):
            continue
        # Skip year-like numbers (e.g. "(2026)" in enclosed, or free-text years)
        if _is_year(token.text):
            token.kind = TokenKind.EXTRA
            continue
        if token.enclosed:
            token.kind = TokenKind.EPISODE
            return
        if token.position > 0:
            idx = tokens.index(token)
            if idx > 0:
                prev = tokens[idx - 1]
                if prev.kind in (
                    TokenKind.UNKNOWN,
                    TokenKind.TITLE_ZH,
                    TokenKind.TITLE_EN,
                    TokenKind.TITLE_JP,
                    TokenKind.SEASON,
                    TokenKind.EXTRA,
                ):
                    token.kind = TokenKind.EPISODE
                    return


def _resolve_group(tokens: list[Token]) -> None:
    for token in tokens:
        if token.enclosed and token.kind == TokenKind.UNKNOWN:
            token.kind = TokenKind.GROUP
            return


def _resolve_prefix_tags(tokens: list[Token]) -> None:
    for token in tokens:
        if token.kind != TokenKind.UNKNOWN:
            continue
        if _PREFIX_TAG_RE.match(token.text):
            token.kind = TokenKind.PREFIX_TAG
            continue
        stripped = _PREFIX_STRIP_RE.sub("", token.text).strip()
        if stripped != token.text:
            token.text = stripped


def _resolve_region_recruit(tokens: list[Token]) -> None:
    for token in tokens:
        if token.kind != TokenKind.UNKNOWN:
            continue
        if _REGION_RE.search(token.text):
            token.text = _REGION_RE.sub("", token.text).strip()
            if not token.text:
                token.kind = TokenKind.EXTRA
        if _RECRUIT_RE.search(token.text):
            token.text = _RECRUIT_RE.sub("", token.text).strip()
            if not token.text:
                token.kind = TokenKind.EXTRA


def _split_mixed_language_tokens(tokens: list[Token]) -> None:
    """Split UNKNOWN tokens that contain both CJK and Latin text."""
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.kind != TokenKind.UNKNOWN:
            i += 1
            continue

        text = token.text.strip()
        if not text or not (_has_cjk(text) and _has_latin(text)):
            i += 1
            continue

        parts = _split_mixed_title(text)
        if len(parts) <= 1:
            i += 1
            continue

        new_tokens = []
        for p in parts:
            p = p.strip()
            if p:
                new_tokens.append(
                    Token(
                        text=p,
                        kind=TokenKind.UNKNOWN,
                        position=token.position,
                        enclosed=token.enclosed,
                    )
                )

        if len(new_tokens) > 1:
            tokens[i : i + 1] = new_tokens
            i += len(new_tokens)
        else:
            i += 1


def _resolve_titles(tokens: list[Token]) -> None:
    unknowns = [t for t in tokens if t.kind == TokenKind.UNKNOWN]

    has_zh = False
    has_en = False
    has_jp = False

    for token in unknowns:
        text = token.text.strip()
        if not text:
            token.kind = TokenKind.EXTRA
            continue

        # Extract embedded season
        season_match = _SEASON_EMBEDDED.match(text)
        if season_match:
            title_part = season_match.group(1).strip()
            season_str = season_match.group(2)
            token.text = title_part
            text = title_part
            season_raw = f"第{season_str}季"
            season_tok = Token(
                text=season_raw,
                kind=TokenKind.SEASON,
                position=token.position,
                enclosed=token.enclosed,
            )
            idx = tokens.index(token)
            tokens.insert(idx + 1, season_tok)

        # Handle "number + CJK" titles
        num_match = _NUM_PREFIX_CJK.match(text)
        if num_match and not has_zh:
            token.kind = TokenKind.TITLE_ZH
            has_zh = True
            continue

        lang = _classify_title_lang(text)

        if lang == TokenKind.TITLE_JP and not has_jp:
            token.kind = TokenKind.TITLE_JP
            has_jp = True
        elif lang == TokenKind.TITLE_ZH and not has_zh:
            token.kind = TokenKind.TITLE_ZH
            has_zh = True
        elif lang == TokenKind.TITLE_EN and not has_en:
            token.kind = TokenKind.TITLE_EN
            has_en = True
        else:
            token.kind = TokenKind.EXTRA
