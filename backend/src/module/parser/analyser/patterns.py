import re

LAST_BACKET_PATTERN = re.compile(
    r"[\(\（][^\(\)（）]*[\)\）](?!.*[\(\（][^\(\)（）]*[\)\）])"
)
BOUNDARY_START = r"[\s_\-\.\[\]/\)\(（）]"
BOUNDARY_END = r"(?=[\s_\.\-\[\]/\)\(（）])"  # 结束边界（不消耗）


EPISODE_PATTERN = re.compile(
    rf""" {BOUNDARY_START}
    (第?(\d+?)[话話集]
    |S\d+?(?:EP?(\d+?))
    |EP?(\d+?)
    |-\s(\d+?)
    |(\d+?).?v\d
    |(\d+?).?END
    |(\d+?)pre)
    {BOUNDARY_END}
""",
    re.VERBOSE | re.IGNORECASE,
)

EPISODE_RE_UNTRUSTED = re.compile(
    rf"""{BOUNDARY_START}
        ((\d+?))
        {BOUNDARY_END}
        """,
    re.VERBOSE,
)

SEASON_RE = re.compile(
    rf"""
    {BOUNDARY_START}
    (第(.{{1,3}})季       # 匹配"第...季"格式
    |第(.{{1,3}})期        # 匹配"第...期"格式
    |第.{{1,3}}部分      # 匹配"第...部分"格式
    |[Ss]eason\s(\d{{1,2}})  # 匹配"Season X"格式
    |[Ss](\d{{1,2}})         # 匹配"SX"格式
    |(\d+)[r|n]d(?:\sSeason)?  # 匹配"Xnd Season"格式
    |part \d   #part 6
    |(IV|III|II|I)            # 匹配罗马数字
    ) (?=[\s_\.\-\[\]/\)\($E])  # 结束边界（不消耗）
    """,
    re.VERBOSE,
)

SEASON_PATTERN_UNTRUSTED = re.compile(r"\d+")

VIDEO_TYPE_PATTERN = re.compile(
    rf"""
    {BOUNDARY_START}# Frame rate
    (23.976FPS
    |24FPS
    |29.97FPS
    |[30|60|120]FPS
    # Video codec
    |8-?BITS?
    |10-?BITS?
    |HI10P?
    |[HX].?26[4|5]
    |AVC
    |HEVC2?
    # Video format
    |AVI
    |RMVB
    |MKV
    |MP4
    # video quailty
    |HD
    |BD
    |UHD
    |SRT[x2].?
    |ASS[x2].? # AAAx2
    |PGS
    |V[123]
    |OVA)
    {BOUNDARY_END}
    """,
    re.VERBOSE | re.IGNORECASE,
)

AUDIO_INFO = re.compile(
    f"""
    {BOUNDARY_START}# Frame rate
    (AAC(?:x2)?
    |FLAC
    |DDP
    )
    {BOUNDARY_END}
    """,
    re.VERBOSE | re.IGNORECASE,
)

RESOLUTION_RE = re.compile(
    rf"""
    {BOUNDARY_START}
    (\d{{3,4}}[×xX]\d{{3,4}}
    |1080p?
    |720p?
    |480p?
    |2160p?
    |4K
    )
    {BOUNDARY_END}
    """,
    re.IGNORECASE | re.VERBOSE,
)

SOURCE_RE = re.compile(
    rf"""
    {BOUNDARY_START}
    (B-Global
    |Baha
    |Bilibili
    |AT-X
    |W[eE][Bb]-?(?:Rip)?(?:DL)? # WEBRIP 和 WEBDL
    |CR
    |ABEMA
    |viutv[粤语]*?)
    {BOUNDARY_END}
    """,
    re.VERBOSE | re.IGNORECASE,
)

SUB_RE = re.compile(
    rf"""
    {BOUNDARY_START}
    ((?:[(BIG5|CHS|CHT|GB|JP)_简中繁日英外字幕挂内封嵌双语文体]+)
    |CHT
    |CHS
    |BIG5
    |CHI
    |JA?P
    |GB
    |HardSub)
    {BOUNDARY_END}
    """,
    re.VERBOSE,
)
PREFIX_RE = re.compile(r"[^\w\s\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff-]")


UNUSEFUL_RE = re.compile(
    # 匹配无用的片段
    rf"""(?<={BOUNDARY_START})   
        ( .?[\d一四七十春夏秋冬季]{{1,2}}月(新番|短剧).*?
        | 港澳台地区
        | 国漫
        | END
        | 招募.*?
        | \d{{4}}年\d{{1,2}}月.*? # 2024年1月
        | \d{{4}}\.\d{{1,2}}\.\d{{1,2}}
        |[网盘无水印高清下载迅雷]{{4,10}})
        {BOUNDARY_END}""",
    re.VERBOSE,
)

V1_RE = re.compile(
    rf"""
    {BOUNDARY_START}
    (V1)
    {BOUNDARY_END}
    """,
    re.VERBOSE | re.IGNORECASE,
)

POINT_5_RE = re.compile(
    r"""(第?\d+?\.\d+?[话話集]
    |EP?\d+?\.\d+?
    |-\s\d+?\.\d+?
    |\d+?\.\d+?v\d+?
    |\d+?\.\d+?(END|pre)
    )
    (?=[\s_\-\[\]$\.\(\)])
""",
    re.VERBOSE | re.IGNORECASE,
)

CHINESE_PATTERN = re.compile(r"[\u4e00-\u9fff]")  # 中文字符
JAPANESE_PATTERN = re.compile(r"[\u3040-\u309f\u30a0-\u30ff]")  # 日文
MIXED_PATTERN = re.compile(r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]+")  # 中日文混合
