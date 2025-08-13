import re

LAST_BACKET_PATTERN = re.compile(
    r"[\(\（][^\(\)（）]*[\)\）](?!.*[\(\（][^\(\)（）]*[\)\）])"
)

split_pattern = r"/_&（）\s\-\.\[\]\(\)"
BOUNDARY_START = rf"[{split_pattern}]"  # 开始边界（不消耗）
BOUNDARY_END = rf"(?={BOUNDARY_START})"  # 结束边界（不消耗）


EPISODE_PATTERN = re.compile(
    rf""" {BOUNDARY_START}
    (第?(\d+?)[话話集]
    |S\d+?(?:EP?(\d+?))
    |EP?(\d+?)
    |-\s(\d+?)
    |(\d+?)v\d
    |(\d+?).?END
    |(\d+?)Fin # -12Fin
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
    |[Ss]eason\s?(\d{{1,2}})  # 匹配"Season X"格式
    |SEASON\s?(\d{{1,2}})  # 匹配"SEASON X"格式
    |[Ss](\d{{1,2}})         # 匹配"SX"格式
    |(\d+)[r|n]d(?:\sSeason)?  # 匹配"Xnd Season"格式
    |part \d   #part 6
    |(IV|III|II|I)            # 匹配罗马数字
    ) (?=[\s_\.\-\[\]/\)\($E])  # 结束边界（不消耗）
    """,
    re.VERBOSE,
)

# TODO: 后期放出去单独更新
GROUP_RE = re.compile(
    rf"""
    {BOUNDARY_START}
    (ANI
    |LoliHouse
    |SweetSub
    |Pre-S
    |H-Enc
    |TOC
    |Billion Meta Lab
    |Lilith-Raws
    |DBD-Raws
    |NEO·QSW
    |SBSUB
    |MagicStar
    |7³ACG
    |KitaujiSub
    |Doomdos
    |Prejudice-Studio
    |GM-Team
    |VCB-Studio
    |神椿观测站
    |极影字幕社
    |百冬练习组
    |猎户手抄部
    |喵萌奶茶屋
    |萌樱字幕组
    |三明治摆烂组
    |绿茶字幕组
    |梦蓝字幕组
    |幻樱字幕组
    |织梦字幕组
    |北宇治字组
    |北宇治字幕组
    |霜庭云花Sub
    |氢气烤肉架
    |豌豆字幕组
    |风之圣殿字幕组
    |黒ネズミたち
    |桜都字幕组
    |漫猫字幕组
    |猫恋汉化组
    |黑白字幕组
    |猎户压制部
    |猎户手抄部
    |沸班亚马制作组
    |星空字幕组
    |光雨字幕组
    |樱桃花字幕组
    |动漫国字幕组
    |动漫国
    |千夏字幕组
    |SW字幕组
    |澄空学园
    |华盟字幕社
    |诸神字幕组
    |雪飘工作室
    |❀拨雪寻春❀
    |夜莺家族
    |YYQ字幕组
    |APTX4869
    |Prejudice-Studio
    |丸子家族
    )
    {BOUNDARY_END}
    """,
    re.VERBOSE,
)

SEASON_PATTERN_UNTRUSTED = re.compile(r"\d+(?!\.)")

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
    |AV1
    |RMVB
    |MKV
    |MP4
    # video quailty
    |HD
    |UHD
    |SRT[x2].?
    |ASS[x2].? # AAAx2
    |PGS
    |V[123]
    |Remux
    |OVA)
    {BOUNDARY_END}
    """,
    re.VERBOSE | re.IGNORECASE,
)

AUDIO_INFO = re.compile(
    f"""
    {BOUNDARY_START}# Frame rate
    (AAC(?:x2)?
    |FLAC(?:x2)?
    |DDP
    |OPUS
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
    |BD(?:RIP)?
    |JPBD
    |viutv[粤语]*?)
    {BOUNDARY_END}
    """,
    re.VERBOSE | re.IGNORECASE,
)


# SUB_BOUNDARY_START = f"(?=[{split_pattern+'简繁中日英体'}])"  # 开始边界
SUB_BOUNDARY_START = f"[{split_pattern+'简繁中日英体内外字'}]"  # 开始边界
SUB_BOUNDARY_END = rf"(?={SUB_BOUNDARY_START})"  # 结束
SUB_RE_CHT = re.compile(
    rf"""
    {SUB_BOUNDARY_START}
    (CHT
    |繁)
    {SUB_BOUNDARY_END}
    """,
    re.VERBOSE | re.IGNORECASE,
)
SUB_RE_CHS = re.compile(
    rf"""
    {SUB_BOUNDARY_START}
    (CHS
    |SC
    |简
    |GB)
    {SUB_BOUNDARY_END}
    """,
    re.VERBOSE | re.IGNORECASE,
)
SUB_RE_JP = re.compile(
    rf"""
    {SUB_BOUNDARY_START}
    (JP
    |日)
    {SUB_BOUNDARY_END}
    """,
    re.VERBOSE | re.IGNORECASE,
)


SUB_RE_ENGLISH = re.compile(
    rf"""
    {SUB_BOUNDARY_START}
    ( 英)
    {SUB_BOUNDARY_END}
    """,
    re.VERBOSE | re.IGNORECASE,
)

SUB_RE_TYPE = re.compile(
    rf"""
    {SUB_BOUNDARY_START}
    (外挂
    |内封
    |内嵌
    |硬字幕
    |软字幕
    |ASS
    |SRT)
    """,
    re.VERBOSE | re.IGNORECASE,
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
        | Vol\.\d-\d #1-6
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

if __name__ == "__main__":
    # Test the patterns
    import re

    title = "[H-Enc] 败犬女主太多了！ / Make Heroine ga Oosugiru! (BDRip 1080p HEVC FLAC) [复制磁连]"
    title = "【澄空学园&华盟字幕社&动漫国字幕组】★04月新番[Summer Pockets][17][1080P][简体][MP4] [复制磁连]"
    title = "[猎户手抄部] 碧蓝之海 第二季 / Grand Blue S2 [01] [1080p] [简繁日内封] [2025年7月番] [复制磁连]"
    title = "[猎户手抄部] 明日方舟：焰烬曙明 / Arknights：Enshin Shomei [05] [JP_CN] [1080p] [简繁内封] [2025年7月番] [复制磁连]"
    if SUB_RE_CHS.search(title):
        print("CHS:", SUB_RE_CHS.search(title))
        print("CHS:", SUB_RE_CHS.search(title)[1])
    else:
        print("CHS not found")
    if SUB_RE_CHT.search(title):

        print("CHS:", SUB_RE_CHT.search(title))
        print("Cht:", SUB_RE_CHT.search(title)[1])
    else:
        print("Cht not found")
    if SUB_RE_JP.search(title):
        print("JP:", SUB_RE_JP.search(title)[1])
    else:
        print("JP not found")
