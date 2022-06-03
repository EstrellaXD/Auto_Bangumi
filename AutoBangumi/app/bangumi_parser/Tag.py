import re
import os, sys
import logging

sys.path.append(os.path.dirname("../utils"))

logger = logging.getLogger(__name__)


# 扒了6W数据，硬找的参数，没啥说的
def get_dpi(file_name):
    dpi_list = [
        "4k",
        "2160p", "1440p", "1080p+", "1080p", "1036p", "816p", "810p", "720p",
        "576p", "544P", "540p", "480p", "360p",
        "1080i", "1080+",
        "3840x2160", "1920x1080", "1920x1036", "1920x804", "1920x800",
        "1536x864", "1452x1080", "1440x1080", "1280x720", "1272x720", "1255x940", "1024x768", "1024X576",
        "960x720", "948x720", "896x672", "872x480", "848X480", "832x624", "704x528", "640x480",
    ]
    for i in dpi_list:
        dpi = str(file_name).lower().find(i)
        if dpi > 0:
            if "x" in i:
                return int(i.split("x")[-1])
            elif "p" in i or "i" in i or "+" in i:
                return int(i.strip("p").strip("i").strip("+"))
            elif "4k" in i:
                return 4096
    return None


# 获取语种
def get_language(file_name):
    lang = []
    # 中文标示
    try:
        lang.append(
            re.search(
                "[（(\[【 .]((tvb|内地)?([中日国粤简繁英俄双雙语字幕][双雙语文體体字幕&/]?[_&+]?)+)[）)\]】]?",
                str(file_name),
            )
            .group(1)
            .strip(" ")
        )
    except Exception as e:
        # logger.info(e)
        pass
    # 中文标示
    try:
        lang.append(
            re.search("[（(\[【.]?([日粤国中简繁英俄文体][语字]?(双?幕?))*[）)\]】]?", str(file_name))
            .group(1)
            .strip(" ")
        )
    except Exception as e:
        # logger.info(e)
        pass
    # 英文标示
    try:
        lang = lang + re.search(
            "[（(\[【]?(((G?BIG5|CHT|CHS|GB|JPN?|CN)[/ _]?){1,3})[）)\]】]?",
            str(file_name),
        ).group(1).lower().strip(" ").split(" ")
    except Exception as e:
        # logger.info(e)
        pass
    if lang:
        return lang
    else:
        return None


# 文件种类
def get_type(file_name):
    type_list = []
    # 英文标示
    try:
        type_list.append(
            re.search(
                "[（(\[【]?(((mp4|mkv|mp3)[ -]?){1,3})[）)\]】]?",
                str(file_name).lower(),
            )
            .group(1)
            .strip(" ")
        )
    except Exception as e:
        # logger.info(e)
        pass
    if type_list:
        return type_list
    else:
        return None


# 编码格式
def get_code(file_name):
    code = []
    # 视频编码
    try:
        code = code + re.search(
            "[（(\[【]?([ _-]?([xh]26[45]|hevc|avc)){1,5}[ ）)\]】]?",
            str(file_name).lower(),
        ).group(1).split(" ")
    except Exception as e:
        # logger.info(e)
        pass
    # 位深
    try:
        code = code + re.search(
            "[（(\[【]?[ _-]?((10|8)[ -]?bit)[ ）)\]】]?", str(file_name).lower()
        ).group(1).split(" ")
    except Exception as e:
        # logger.info(e)
        pass
    # 音频编码
    try:
        code = code + re.search(
            "[（(\[【]?(([ _-]?((flac(x\d)?|aac|mp3|opus)(x\d)?)){1,5})[ ）)\]】]?",
            str(file_name).lower(),
        ).group(3).split(" ")
    except Exception as e:
        # logger.info(e)
        pass
    if code:
        while "" in code:
            code.remove("")
        return code
    else:
        return None


# 来源
def get_source(self):
    file_name = str(self.name.raw).lower()
    type_list = []
    # 英文标示
    for _ in range(3):
        try:
            res = (
                re.search(
                    "[（(\[【]?((bd|dvd|hd|remux|(viu)?tvb?|ani-one|bilibili|网飞(动漫)|b-?global|baha|web[ /-]?(dl|rip))[ -]?(b[o0]x|iso|mut|rip)?)[）)\]】]?",
                    file_name,
                )
                .group(1)
                .lower()
                .strip(" ")
            )
            if res not in type_list:
                type_list.append(res)
        except Exception as e:
            # logger.info(e)
            pass
        for res in type_list:
            file_name = file_name.replace(res, "")
    if type_list:
        return type_list
    else:
        return None


# 获取版本
def get_vision(file_name):
    vision = []
    # 中文
    try:
        vision.append(
            re.search(
                "[（(\[【]?(([\u4e00-\u9fa5]{0,5}|[Vv]\d(重校)?|VCD)((版本?|修[复正]|WEB限定)|片源|内详|(特别篇))(话|版|合?集?))[）)\]】]?",
                str(file_name),
            ).group(1)
        )
    except Exception as e:
        # logger.info(e)
        pass
    # 英文
    try:
        vision.append(
            re.search(
                "[（(\[【 ]\d{1,2}((v\d)((版本?|修复?正?版)|片源?|内详)?)[）)\]】]",
                str(file_name),
            ).group(1)
        )
    except Exception as e:
        # logger.info(e)
        pass
    # [v2]
    try:
        vision.append(re.search("[（(\[【 ](v\d)[）)\]】]", str(file_name)).group(1))
    except Exception as e:
        # logger.info(e)
        pass
    if vision:
        return vision
    else:
        return None


# 获取字幕类型
def get_ass(file_name):
    ass = []
    # 中文标示
    try:
        ass.append(
            re.search(
                "[（(\[【]?(附?([内外][挂嵌封][+&]?){1,2}(字幕|[简中日英]*音轨)?)[）)\]】]?",
                str(file_name),
            ).group(1)
        )
    except Exception as e:
        # logger.info(e)
        pass
    # 英文标示
    try:
        ass.append(
            re.search(
                "[ （(\[【+](([ +]?(ass|pgs|srt)){1,3})[）)\]】]?", str(file_name)
            )
            .group(1)
            .strip(" ")
        )
    except Exception as e:
        # logger.info(e)
        pass
    if ass:
        return ass
    else:
        return None
