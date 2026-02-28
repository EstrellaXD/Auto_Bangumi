import re

from module.models import Episode

from .keywords import CHINESE_NUMBER_MAP
from .token import Token, TokenKind

# Only strip dashes that have surrounding whitespace (separators),
# not dashes attached to characters (part of titles like 地。-关于地球的运动-)
_DASH_STRIP = re.compile(r"^\s*-\s+|\s+-\s*$")
_SEASON_NUM = re.compile(r"[Ss](\d+)|Season\s+(\d+)", re.I)
_CHINESE_SEASON = re.compile(r"第([一二三四五六七八九十\d]+)[季期]")
_SUB_CLEAN = re.compile(r"_MP4|_MKV", re.I)
_CJK_SUB = re.compile(r"[简繁日字幕]")
_NON_EPISODIC_EXTRA = re.compile(r"合集|总集篇|總集篇|特典")


def compose(tokens: list[Token]) -> Episode | None:
    title_en: str | None = None
    title_zh: str | None = None
    title_jp: str | None = None
    season = 1
    season_raw = ""
    episode = 0
    sub: str | None = None
    group = ""
    resolution: str | None = None
    source: str | None = None

    episode_type = "episode"
    has_episode_marker = False
    has_non_episodic_extra = False

    # Collect all subtitles, prefer CJK ones
    all_subs: list[str] = []

    for token in tokens:
        kind = token.kind
        text = token.text

        if kind == TokenKind.GROUP:
            group = text
        elif kind == TokenKind.TITLE_ZH:
            text = _DASH_STRIP.sub("", text).strip()
            if text:
                title_zh = text
        elif kind == TokenKind.TITLE_EN:
            title_en = text.strip()
        elif kind == TokenKind.TITLE_JP:
            title_jp = text.strip()
        elif kind == TokenKind.EPISODE:
            has_episode_marker = True
            ep_digits = re.search(r"\d+", text)
            if ep_digits:
                episode = int(ep_digits.group())
        elif kind == TokenKind.SEASON:
            m = _SEASON_NUM.match(text)
            if m:
                s_num = int(m.group(1) or m.group(2))
            else:
                cm = _CHINESE_SEASON.match(text)
                if cm:
                    s_val = cm.group(1)
                    try:
                        s_num = int(s_val)
                    except ValueError:
                        s_num = CHINESE_NUMBER_MAP.get(s_val, 1)
                else:
                    s_num = season
            # Prefer first season found (Chinese season over English)
            if season == 1 or not season_raw:
                season = s_num
                season_raw = text
        elif kind == TokenKind.RESOLUTION:
            if resolution is None:
                resolution = text
        elif kind == TokenKind.SOURCE:
            if source is None:
                source = text
        elif kind == TokenKind.MOVIE:
            episode_type = "movie"
        elif kind == TokenKind.SPECIAL:
            episode_type = "special"
            season = 0
            special_digits = re.search(r"\d+", text)
            if special_digits:
                episode = int(special_digits.group())
        elif kind == TokenKind.EXTRA and _NON_EPISODIC_EXTRA.search(text):
            has_non_episodic_extra = True
        elif kind == TokenKind.SUBTITLE:
            cleaned = _SUB_CLEAN.sub("", text)
            if cleaned:
                all_subs.append(cleaned)

    # Prefer CJK subtitle markers over technical ones
    if all_subs:
        cjk_subs = [s for s in all_subs if _CJK_SUB.search(s)]
        sub = cjk_subs[0] if cjk_subs else all_subs[0]

    if (
        episode_type == "episode"
        and not has_episode_marker
        and not has_non_episodic_extra
    ):
        return None

    return Episode(
        title_en=title_en,
        title_zh=title_zh,
        title_jp=title_jp,
        season=season,
        season_raw=season_raw,
        episode=episode,
        sub=sub,
        group=group,
        resolution=resolution,
        source=source,
        episode_type=episode_type,
    )
