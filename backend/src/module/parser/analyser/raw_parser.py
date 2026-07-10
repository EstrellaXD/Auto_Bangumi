import logging
import re

from module.models import Episode

logger = logging.getLogger(__name__)

EPISODE_RE = re.compile(r"\d+")
TITLE_RE = re.compile(
    r"(.*?|\[.*])((?: ?-) ?\d+(?:[vV]\d{1,2})? |\[\d+]|\[\d+.?[vV]\d]|第\d+[话話集]|\[第?\d+[话話集]]|\[\d+.?END]|[Ee][Pp]?\d+(?![A-Za-z0-9]))(.*)"
)
RESOLUTION_RE = re.compile(r"1080|720|2160|4K")
SOURCE_RE = re.compile(r"B-Global|[Bb]aha|[Bb]ilibili|AT-X|Web")
SUB_RE = re.compile(r"[简繁日字幕]|CH|BIG5|GB")

FALLBACK_EP_PATTERNS = [
    re.compile(r" (\d+) ?(?=\[)"),  # #876/#910: digits before [
    re.compile(r"\[(\d+)\(\d+\)\]"),  # #773: [02(57)]
]

PREFIX_RE = re.compile(r"[^\w\s\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff-]")

# 以下均为静态正则：预编译成模块级 Pattern 对象，避免 process() 内层每次调用都
# 走 re.xxx(pattern_string, ...) 的内部编译缓存查找（profile 显示这部分开销占
# raw_parser 单次调用总耗时的 ~20%，见 2026-07 性能优化）。语义与原来的
# re.search/sub/split/match/findall(r"...", ...) 完全一致。
_BRACKET_CLEAR_RE = re.compile(r"[\[\]]")
_XINFAN_RE = re.compile(r"新番|月?番")
_HK_MO_TW_RE = re.compile(r"港澳台地区")
SEASON_RULE_RE = re.compile(r"S\d{1,2}|Season \d{1,2}|[第].[季期]")
_SEASON_WORD_RE = re.compile(r"Season|S")
_SEASON_CN_RE = re.compile(r"[第 ].*[季期(部分)]|部分")
_SEASON_CN_STRIP_RE = re.compile(r"[第季期 ]")
_HK_MO_TW_BRACKET_RE = re.compile(r"[(（]仅限港澳台地区[）)]")
_NAME_SPLIT_RE = re.compile(r"/|\s{2}|-\s{2}")
_UNDERSCORE_RE = re.compile(r"_{1}")
_DASH_SPACE_RE = re.compile(r" - {1}")
_DIGIT_CN_RE = re.compile(r"\d+\s[一-龥]")
_CN_PREFIX_RE = re.compile(r"^[一-龥]{2,}")
_JP_RE = re.compile(r"[ࠀ-一]{2,}")
_CN_RE = re.compile(r"[一-龥]{2,}")
_EN_RE = re.compile(r"[a-zA-Z]{3,}")
_TAG_BRACKET_RE = re.compile(r"[\[\]()（）]")
_SUFFIX_STRIP_RE = re.compile(r"_MP4|_MKV")

# movie token: hits route the title to episode_type="movie" (no episode number required)
MOVIE_TOKEN_RE = re.compile(r"剧场版|劇場版|电影版|[Mm]ovie")
# OVA / OAD / SP / Special token: hits route the title to episode_type="special",
# season is forced to 0 (Season 0). Digits directly after the token (e.g. "OVA01")
# must also be recognized, so the token itself allows a trailing number.
SPECIAL_TOKEN_RE = re.compile(
    r"\bOVA\d*\b|\bOAD\d*\b|\bSP\d*\b|[Ss]pecial|番外篇?|特别篇"
)
# digits directly after OVA/OAD/SP are treated as the episode number, e.g. "OVA01", "SP 02"
SPECIAL_EPISODE_RE = re.compile(r"(?:OVA|OAD|SP)\s*[-_]?\s*(\d{1,3})", re.I)
BRACKET_RE = re.compile(r"[\[\(（【].*?[\]\)）】]")


def _detect_non_episodic_type(content_title: str) -> str | None:
    """识别剧场版/OVA/OAD/SP/Special 等非常规编号资源的类型。"""
    if MOVIE_TOKEN_RE.search(content_title):
        return "movie"
    if SPECIAL_TOKEN_RE.search(content_title):
        return "special"
    return None


def _parse_non_episodic(content_title: str, group: str, episode_type: str) -> tuple:
    """解析剧场版/OVA/OAD/SP/Special 标题：提炼标题与可选的集数信息，不依赖常规的
    TITLE_RE / fallback 集数匹配。"""
    stripped = prefix_process(content_title, group)
    brackets = BRACKET_RE.findall(stripped)
    name_part = BRACKET_RE.sub(" ", stripped)
    name_part = MOVIE_TOKEN_RE.sub(" ", name_part)
    name_part = SPECIAL_TOKEN_RE.sub(" ", name_part)
    name_part = name_part.strip(" -/")
    name_en, name_zh, name_jp = "", "", ""
    try:
        name_en, name_zh, name_jp = name_process(name_part)
    except ValueError:
        pass
    sub, dpi, source = find_tags(" ".join(brackets))
    ep_match = SPECIAL_EPISODE_RE.search(stripped)
    episode = int(ep_match.group(1)) if ep_match else 0
    season = 0 if episode_type == "special" else 1
    return (
        name_en,
        name_zh,
        name_jp,
        season,
        "",
        episode,
        sub,
        dpi,
        source,
        group,
        episode_type,
    )


def _fallback_parse(content_title: str) -> tuple | None:
    """Try fallback regex patterns when TITLE_RE fails."""
    for pattern in FALLBACK_EP_PATTERNS:
        m = pattern.search(content_title)
        if m:
            season_info = content_title[: m.start()].strip()
            episode_info = m.group(1)
            other = content_title[m.end() :].strip()
            return season_info, episode_info, other
    return None


CHINESE_NUMBER_MAP = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def get_group(name: str) -> str:
    parts = _BRACKET_CLEAR_RE.split(name)
    if len(parts) > 1:
        return parts[1]
    return ""


def pre_process(raw_name: str) -> str:
    return raw_name.replace("【", "[").replace("】", "]")


def prefix_process(raw: str, group: str) -> str:
    # Guard against empty group: without this, the pattern degenerates to ".."
    # and every pair of characters gets deleted, destroying titles that lack a
    # [group] prefix (#1025).
    if group:
        raw = re.sub(f".{re.escape(group)}.", "", raw)
    raw_process = PREFIX_RE.sub("/", raw)
    arg_group = raw_process.split("/")
    while "" in arg_group:
        arg_group.remove("")
    if len(arg_group) == 1:
        arg_group = arg_group[0].split(" ")
    for arg in arg_group:
        if _XINFAN_RE.search(arg) and len(arg) <= 5:
            raw = re.sub(f".{re.escape(arg)}.", "", raw)
        elif _HK_MO_TW_RE.search(arg):
            raw = re.sub(f".{re.escape(arg)}.", "", raw)
    return raw


def season_process(season_info: str):
    name_season = season_info
    # if re.search(r"新番|月?番", season_info):
    #     name_season = re.sub(".*新番.", "", season_info)
    #     # 去除「新番」信息
    # name_season = re.sub(r"^[^]】]*[]】]", "", name_season).strip()
    name_season = _BRACKET_CLEAR_RE.sub(" ", name_season)
    seasons = SEASON_RULE_RE.findall(name_season)
    if not seasons:
        return name_season, "", 1
    name = SEASON_RULE_RE.sub("", name_season)
    for season in seasons:
        season_raw = season
        if _SEASON_WORD_RE.search(season) is not None:
            season = int(_SEASON_WORD_RE.sub("", season))
            break
        elif _SEASON_CN_RE.search(season) is not None:
            season_pro = _SEASON_CN_STRIP_RE.sub("", season)
            try:
                season = int(season_pro)
            except ValueError:
                season = CHINESE_NUMBER_MAP[season_pro]
            break
    return name, season_raw, season


def name_process(name: str):
    name_en, name_zh, name_jp = None, None, None
    name = name.strip()
    name = _HK_MO_TW_BRACKET_RE.sub("", name)
    split = _NAME_SPLIT_RE.split(name)
    while "" in split:
        split.remove("")
    if len(split) == 1:
        if _UNDERSCORE_RE.search(name) is not None:
            split = name.split("_")
        elif _DASH_SPACE_RE.search(name) is not None:
            split = name.split("-")
    if len(split) == 1:
        # Titles like "29 岁单身..." — digits + Chinese are one title
        if _DIGIT_CN_RE.match(split[0]):
            name_zh = split[0].strip()
            return name_en, name_zh, name_jp
        split_space = split[0].split(" ")
        for idx in [0, -1]:
            if _CN_PREFIX_RE.search(split_space[idx]) is not None:
                chs = split_space[idx]
                split_space.remove(chs)
                split = [chs, " ".join(split_space)]
                break
    for item in split:
        if _JP_RE.search(item) and not name_jp:
            name_jp = item.strip()
        elif _CN_RE.search(item) and not name_zh:
            name_zh = item.strip()
        elif _EN_RE.search(item) and not name_en:
            name_en = item.strip()
    return name_en, name_zh, name_jp


def find_tags(other):
    elements = _TAG_BRACKET_RE.sub(" ", other).split(" ")
    # find CHT
    sub, resolution, source = None, None, None
    for element in filter(lambda x: x != "", elements):
        if SUB_RE.search(element):
            sub = element
        elif RESOLUTION_RE.search(element):
            resolution = element
        elif SOURCE_RE.search(element):
            source = element
    return clean_sub(sub), resolution, source


def clean_sub(sub: str | None) -> str | None:
    if sub is None:
        return sub
    return _SUFFIX_STRIP_RE.sub("", sub)


def process(raw_title: str):
    raw_title = raw_title.strip().replace("\n", " ")
    content_title = pre_process(raw_title)
    # 预处理标题
    group = get_group(content_title)
    # 翻译组的名字
    match_obj = TITLE_RE.match(content_title)
    if match_obj is not None:
        season_info, episode_info, other = [x.strip() for x in match_obj.groups()]
    else:
        fallback = _fallback_parse(content_title)
        if fallback is None:
            # 常规集数解析失败：识别剧场版/OVA/OAD/SP/Special 等非常规编号资源，
            # 而非直接丢弃 (原先返回 None 会导致这些资源被整体丢弃)
            episode_type = _detect_non_episodic_type(content_title)
            if episode_type is not None:
                return _parse_non_episodic(content_title, group, episode_type)
            return None
        season_info, episode_info, other = fallback
    process_raw = prefix_process(season_info, group)
    # 处理 前缀
    raw_name, season_raw, season = season_process(process_raw)
    # 处理 第n季
    name_en, name_zh, name_jp = "", "", ""
    try:
        name_en, name_zh, name_jp = name_process(raw_name)
        # 处理 名字
    except ValueError:
        pass
    # 处理 集数
    raw_episode = EPISODE_RE.search(episode_info)
    episode = 0
    if raw_episode is not None:
        episode = int(raw_episode.group())
    sub, dpi, source = find_tags(other)  # 剩余信息处理
    return (
        name_en,
        name_zh,
        name_jp,
        season,
        season_raw,
        episode,
        sub,
        dpi,
        source,
        group,
        "episode",
    )


def raw_parser(raw: str) -> Episode | None:
    ret = process(raw)
    if ret is None:
        logger.info(f"Cannot parse resource: {raw}, skipping.")
        return None
    (
        name_en,
        name_zh,
        name_jp,
        season,
        sr,
        episode,
        sub,
        dpi,
        source,
        group,
        episode_type,
    ) = ret
    return Episode(
        name_en,
        name_zh,
        name_jp,
        season,
        sr,
        episode,
        sub,
        group,
        dpi,
        source,
        episode_type,
    )


if __name__ == "__main__":
    title = "[动漫国字幕组&LoliHouse] THE MARGINAL SERVICE - 08 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕]"
    print(raw_parser(title))
    title = "[北宇治字幕组&LoliHouse] 地。-关于地球的运动- / Chi. Chikyuu no Undou ni Tsuite 03 [WebRip 1080p HEVC-10bit AAC ASSx2][简繁日内封字幕]"
    print(raw_parser(title))
    title = "[御坂字幕组] 男女之间存在纯友情吗？（不，不存在!!）-01 [WebRip 1080p HEVC10-bit AAC] [简繁日内封] [急招翻校轴]"
    print(raw_parser(title))
