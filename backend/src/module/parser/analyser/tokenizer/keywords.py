import re

from .token import TokenKind

KEYWORDS: dict[str, TokenKind] = {
    # Resolution
    "1080p": TokenKind.RESOLUTION,
    "720p": TokenKind.RESOLUTION,
    "2160p": TokenKind.RESOLUTION,
    "4k": TokenKind.RESOLUTION,
    "1080": TokenKind.RESOLUTION,
    "720": TokenKind.RESOLUTION,
    "2160": TokenKind.RESOLUTION,
    "1920x1080": TokenKind.RESOLUTION,
    "3840x2160": TokenKind.RESOLUTION,
    # Source
    "baha": TokenKind.SOURCE,
    "b-global": TokenKind.SOURCE,
    "bilibili": TokenKind.SOURCE,
    "at-x": TokenKind.SOURCE,
    "web-dl": TokenKind.SOURCE,
    "webrip": TokenKind.SOURCE,
    "webdl": TokenKind.SOURCE,
    "web": TokenKind.SOURCE,
    "web-dl remux": TokenKind.SOURCE,
    "ttfc": TokenKind.SOURCE,
    "cr": TokenKind.SOURCE,
    "adn": TokenKind.SOURCE,
    "iqiyi": TokenKind.SOURCE,
    "abema": TokenKind.SOURCE,
    # Codec
    "hevc": TokenKind.CODEC,
    "avc": TokenKind.CODEC,
    "x264": TokenKind.CODEC,
    "x265": TokenKind.CODEC,
    "hevc-10bit": TokenKind.CODEC,
    "hevc10-bit": TokenKind.CODEC,
    "h264": TokenKind.CODEC,
    "h265": TokenKind.CODEC,
    "h.264": TokenKind.CODEC,
    "h.265": TokenKind.CODEC,
    "10bit": TokenKind.CODEC,
    # Audio
    "aac": TokenKind.AUDIO,
    "flac": TokenKind.AUDIO,
    "mp3": TokenKind.AUDIO,
    "ac3": TokenKind.AUDIO,
    "dts": TokenKind.AUDIO,
    # Container
    "mp4": TokenKind.CONTAINER,
    "mkv": TokenKind.CONTAINER,
    "avi": TokenKind.CONTAINER,
    # Subtitle markers
    "cht": TokenKind.SUBTITLE,
    "chs": TokenKind.SUBTITLE,
    "big5": TokenKind.SUBTITLE,
    "gb": TokenKind.SUBTITLE,
    "assx2": TokenKind.SUBTITLE,
    "multi sub": TokenKind.SUBTITLE,
    "vostfr": TokenKind.SUBTITLE,
    # Movie markers
    "movie": TokenKind.MOVIE,
    "gekijouban": TokenKind.MOVIE,
    "the movie": TokenKind.MOVIE,
    # Version
    "v2": TokenKind.VERSION,
    "v3": TokenKind.VERSION,
    # End marker
    "end": TokenKind.END_MARKER,
}


PATTERN_CHECKS: list[tuple[re.Pattern, TokenKind]] = [
    # Episode patterns
    (re.compile(r"^[Ee][Pp]?\d+$"), TokenKind.EPISODE),
    (re.compile(r"^第?\d+[话話集]$"), TokenKind.EPISODE),
    (re.compile(r"^\d+[Pp]$"), TokenKind.RESOLUTION),
    (re.compile(r"^\d{3,4}[xX]\d{3,4}$"), TokenKind.RESOLUTION),
    # Season patterns
    (re.compile(r"^[Ss]\d{1,2}$"), TokenKind.SEASON),
    (re.compile(r"^Season \d+$", re.I), TokenKind.SEASON),
    (re.compile(r"^第[一二三四五六七八九十\d]+[季期]$"), TokenKind.SEASON),
    # S01E05 combined pattern
    (re.compile(r"^[Ss]\d{1,2}[Ee]\d+$"), TokenKind.EPISODE),
    # Subtitle patterns
    (re.compile(r"^[简繁日字幕][简繁日字幕体文]*"), TokenKind.SUBTITLE),
    (re.compile(r"^GB_?(?:JP|MP4|MKV)?$", re.I), TokenKind.SUBTITLE),
    (re.compile(r"^CHS_JP$", re.I), TokenKind.SUBTITLE),
    (re.compile(r"^CHT_JP$", re.I), TokenKind.SUBTITLE),
    # Prefix tags
    (re.compile(r"^\d+月新番$"), TokenKind.PREFIX_TAG),
    (re.compile(r"^新番$"), TokenKind.PREFIX_TAG),
    (re.compile(r"^★.*★$"), TokenKind.PREFIX_TAG),
    # Version pattern
    (re.compile(r"^[vV]\d$"), TokenKind.VERSION),
    # Hash (CRC32)
    (re.compile(r"^[0-9A-Fa-f]{8}$"), TokenKind.HASH),
    # Movie markers
    (re.compile(r"^[剧劇][场場][版]?$|^劇場版?$"), TokenKind.MOVIE),
    (re.compile(r"^Movie$", re.I), TokenKind.MOVIE),
    (re.compile(r"^Gekijou-?ban$", re.I), TokenKind.MOVIE),
    # Date pattern
    (re.compile(r"^\d{4}\.\d{2}\.\d{2}$"), TokenKind.EXTRA),
    # File size
    (re.compile(r"^\d+\.\d+ [KMGT]B$", re.I), TokenKind.EXTRA),
]

CHINESE_NUMBER_MAP: dict[str, int] = {
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

FILE_EXTENSIONS = re.compile(r"\.(mp4|mkv|avi|ass|srt|ssa|sub)$", re.I)
