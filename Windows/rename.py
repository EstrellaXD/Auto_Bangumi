import re
import json
import time

import zhconv
import requests
import logging
import pandas as pd

from chain_db import ChainDb


class Rename:
    def __init__(self, file_name):
        self.file_name = file_name
        self.clean()
        logging.basicConfig(level=logging.DEBUG,
                            filename='./rename_log.txt',
                            filemode='w',
                            format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')
        self.group_character = ['字幕社', '字幕组', '字幕屋', '发布组', '动漫', '国漫', '汉化', 'raw', 'works', '工作室', '压制', '合成', '制作',
                                '搬运', '委员会', '家族', '译制', '动画', '研究所', 'sub', '翻译', '联盟', 'dream', '-rip', 'neo', 'team']
        self.group_char = ['dmhy', "喵萌", 'lolihouse', 'vcb', '澄空学园', 'c.c动漫', '拨雪寻春', 'mingy', 'amor', 'moozzi2',
                           '酷漫', 'skytree', 'sweetsub', 'pcsub', 'ahu-sub', 'f宅', 'captions', 'dragsterps', 'onestar',
                           '卡通', '时雨初空', 'nyaa', 'ddd', 'koten', 'reinforce', '届恋对邦小队', 'cxraw']
        with open("rule.json", encoding='utf-8') as file_obj:
            rule_json = json.load(file_obj)[0]["group_name"]
        self.group_rule = [str(x).lower() for x in rule_json]
        self.file_info = {}

        self.pre_analyse = None
        self.recognize_group()

    # 获取字符串出现位置
    def get_str_location(self, char, target):
        locate = []
        for index, value in enumerate(char):
            if target == value:
                locate.append(index)
        return locate

    # 匹配某字符串最近的括号
    def get_gp(self, char, string):
        start = [x for x in self.get_str_location(string, "[") if int(x) < int(string.find(char))][-1] + 1
        end = [x for x in self.get_str_location(string, "]") if int(x) > int(string.find(char))][0]
        return string[start:end]

    # 清理原链接（中文字符替换为英文）
    def clean(self):
        file_name = zhconv.convert(self.file_name, 'zh-cn')
        # 去广告
        file_name = re.sub("[（(\[【]?(字幕)?[\u4e00-\u9fa5]{0,3}(新人|招募?新?)[\u4e00-\u9fa5]{0,5}[）)\]】]?", "", file_name)
        # 除杂
        file_name = re.sub("[（(\[【]?★?(\d{4}年[春夏秋冬]?)?[\d一二三四五六七八九十]{1,2}月新?番?★?[）)\]】]?", "", file_name)
        # 除杂x2
        file_name = re.sub("[（(\[【]?(2(\d{3}[年.][春夏秋冬]?)\d{1,2}\.?\d{1,2})[）)\]】]?", "", file_name)
        # 除杂x3
        file_name = re.sub("[（(\[【]检索.*[）)\]】]?", "", file_name)
        strip = ["复制磁连", "兼容", "配音", "网盘", "\u200b", "[]", "★"]
        for i in strip:
            file_name = file_name.replace(i, "")
        self.file_name = str(file_name).replace('：', ':').replace('【', '[').replace('】', ']').replace('-', '-') \
            .replace('（', '(').replace('）', ')').replace("＆", "&").replace("X", "x").replace("×", "x") \
            .replace("Ⅹ", "x").replace("-", " ").replace("_", " ")

    # 检索string1列表元素是否在string2列表元素中
    def find_str(self, str1, str2):
        for s1 in str1:
            for s2 in str2:
                if s1 in s2:
                    return [True, s2[1:]]
        return [False, name]

    # 检索字幕组特征
    def recognize_group(self):
        character = self.group_character
        group = self.group_char
        rule = self.group_rule
        # 字幕组（特例）特征优先级大于通用特征
        character = group + character
        # !强规则，人工录入标准名，区分大小写，优先匹配
        if "[ANi]" in self.file_name:
            self.pre_analyse = "[ani]"
            return "enforce"
        for char in rule:
            if "[%s]" % char in self.file_name:
                self.pre_analyse = char
                return "enforce"
        # 如果文件名以 [字幕组名] 开头
        if self.file_name[0] == "[":
            str_split = self.file_name.lower().split("]")
            # 检索特征值是否位于文件名第1、2、最后一段
            for char in character:
                if char in str_split[0] or char in str_split[1] or char in str_split[-1]:
                    self.pre_analyse = char
                    return "success"
            # 文件名是否为 [字幕组名&字幕组名&字幕组名] ，求求了，一集的工作量真的需要三个组一起做吗
            if self.find_str(["&", "@"], str_split)[0]:
                res = self.find_str(["&", "@"], str_split)[1]
                # 限制匹配长度，防止出bug
                if len(res) < 10:
                    self.pre_analyse = res
                    return "special"
            # 再匹配不上我就麻了
            self.pre_analyse = None
            return False
        # 文件名以 -字幕组名 结尾
        elif "-" in self.file_name:
            for char in character:
                if char in self.file_name.lower().split("-")[-1]:
                    self.pre_analyse = self.file_name.lower().split("-")[-1]
                    return "reserve"
            self.pre_analyse = None
            return False
        # 文件名以空格分隔 字幕组名为第一段
        else:
            for char in character:
                if char in self.file_name.lower().split(" ")[0]:
                    self.pre_analyse = char
                    return "blank"
            self.pre_analyse = None
            return False

    # 获取字幕组名
    def get_group(self):
        # 是否匹配成功（哪种方式匹配成功）
        status = self.recognize_group()
        # 检索到的特征值
        res_char = self.pre_analyse
        # 强条
        if status == "enforce":
            return res_char
        # 大部分情况
        elif status == "success":
            # 如果是 [字幕组名] ，这么标准的格式直接else送走吧，剩下的匹配一下
            if "[%s]" % res_char not in self.file_name.lower():
                if self.file_name[0] == "[":
                    try:
                        # 以特征值为中心，匹配最近的中括号，八成就这个了
                        gp = self.get_gp(res_char, self.file_name.lower())
                        # 防止太长炸了，一般不会这么长的字幕组名
                        if len(gp) > 30:
                            print("name:%s\r\nchar:%s,gp:%s" % (self.file_name, res_char, gp))
                        return gp
                    except Exception as e:
                        print("bug -- res_char:%s,%s,%s" % (res_char, self.file_name.lower(), e))
            else:
                return res_char
        # 文件名以空格分隔 字幕组名为第一段
        elif status == "blank":
            if res_char in self.file_name.lower().split(" ")[0]:
                res = self.file_name.lower().split(" ")[0]
                return res
        # 文件名为 [字幕组名&字幕组名&字幕组名]
        elif status == "special":
            return res_char
        # -字幕组名 在结尾
        elif status == "reserve":
            return res_char
        # 再见
        else:
            return None

    # 扒了6W数据，硬找的参数，没啥说的
    def get_dpi(self):
        file_name = self.file_name
        dpi_list = ["4k", "2160p", "1440p", "1080p", "1036p", "816p", "810p", "720p", "576p", "544P", "540p", "480p",
                    "1080i", "1080+",
                    "3840x2160", "1920x1080", "1920x1036", "1920x804", "1920x800", "1536x864", "1452x1080", "1440x1080",
                    "1280x720", "1272x720", "1255x940", "1024x768", "1024X576", "960x720", "948x720", "896x672",
                    "872x480", "848X480", "832x624", "704x528", "640x480",
                    "mp4_1080", "mp4_720"]
        for i in dpi_list:
            dpi = str(file_name).lower().find(i)
            if dpi > 0:
                return [str(i)]
        return None

    # 获取语种
    def get_language(self):
        file_name = self.file_name
        lang = []
        # 中文标示
        try:
            lang.append(
                re.search("[（(\[【]?((tvb)?(日?[粤中简繁英]日?(文|体|体?双?语)?/?){1,5}(双?字幕)?)[）)\]】]?", str(file_name)).group(
                    1).strip(" "))
        except Exception as e:
            logging.info(e)
        # 英文标示
        try:
            lang = lang + re.search("[（(\[【]?(((G?BIG5|CHT|CHS|GB|JP|CN)[/ _]?){1,3})[）)\]】]?", str(file_name)).group(
                1).lower().strip(" ").split(" ")
        except Exception as e:
            logging.info(e)
        if lang:
            return lang
        else:
            return None

    # 文件种类
    def get_type(self):
        file_name = self.file_name
        type_list = []
        # 英文标示
        try:
            type_list.append(re.search("[（(\[【]?(((flac(x\d)?|mp4|mkv|mp3)[ -]?){1,3})[）)\]】]?",
                                       str(file_name).lower()).group(1).lower().strip(" "))
        except Exception as e:
            logging.info(e)
        if type_list:
            return type_list
        else:
            return None

    # 编码格式
    def get_code(self):
        file_name = self.file_name
        code = []
        # 英文标示
        try:
            code = code + re.search("[（(\[【]?(((x26[45]|hevc|aac|avc|((10|8)[ -]?bit))[ -]?(x\d)?[ -]?){1,5})[ ）)\]】]?",
                                    str(file_name).lower()).group(1).lower().strip(" ").split(" ")
        except Exception as e:
            logging.info(e)
        if code:
            return code
        else:
            return None

    # 来源
    def get_source(self):
        file_name = str(self.file_name).lower()
        type_list = []
        # 英文标示
        for _ in range(3):
            try:
                res = re.search(
                    "[（(\[【]?((bd|remux|(viu)?tvb?|bilibili|b ?global|baha|web[ -]?(dl|rip))[ -]?(iso|mut|rip)?)[）)\]】]?",
                    file_name).group(1).lower().strip(" ")
                if res not in type_list:
                    type_list.append(res)
            except Exception as e:
                logging.info(e)
            for res in type_list:
                file_name = file_name.replace(res, "")
        if type_list:
            return type_list
        else:
            return None

    # 获取季度
    def get_season(self):
        file_name = self.file_name.lower()
        season = []
        # 中文标示
        try:
            season.append(re.search(" ?(第?(\d{1,2}|[一二三]|最终)(部|季|季度|丁目))", str(file_name)).group(1).strip(" "))
        except Exception as e:
            logging.info(e)
        # 英文标示
        try:
            season.append(
                re.search("((final ?)?(season|[ \[]s) ?\d{1,2})", str(file_name)).group(1).strip(" "))
        except Exception as e:
            logging.info(e)
        if season:
            return season
        else:
            return None

    # 获取集数
    def get_episode(self):
        file_name = self.file_name.lower()
        episode = []
        # [10 11]集点名批评这种命名方法，几个国漫的组
        try:
            episode.append(
                re.search("[\[( ](\d{1,3}[- &]\d{1,3}) ?(fin| Fin|\(全集\))?[ )\]]", str(file_name)).group(1))
            return episode
        except Exception as e:
            logging.info(e)
        # 这里匹配ova 剧场版 不带集数的合集 之类的
        try:
            episode.append(
                re.search("[\[ 第](_\d{1,3}集|ova|剧场版|全|OVA ?\d{0,2}|合|[一二三四五六七八九十])[集话章 \]\[]", str(file_name)).group(1))
            return episode
        except Exception as e:
            logging.info(e)
        # 标准单集 sp单集
        try:
            episode.append(
                re.search("[\[ 第e]((sp|(数码)?重映)?(1?\d{1,3}(\.\d)?|1?\d{1,3}\(1?\d{1,3}\)))(v\d)?[集话章 \]\[]",
                          str(file_name)).group(1))
            return episode
        except Exception as e:
            logging.info(e)
        # xx-xx集
        try:
            episode.append(
                re.search("[\[ 第(]((合集)?\\\)?(\d{1,3}[ &]\d{1,3})(话| |]|\(全集\)|全集|fin)", str(file_name)).group(1))
            return episode
        except Exception as e:
            logging.info(e)
        return None

    # 获取版本
    def get_vision(self):
        file_name = self.file_name.lower()
        vision = []
        # 中文
        try:
            vision.append(
                re.search("[（(\[【]?(([\u4e00-\u9fa5]{0,2}|v\d)((版本?|修复?正?)|片源?|内详))[）)\]】]?", str(file_name)).group(1))
        except Exception as e:
            logging.info(e)
        # 英文
        try:
            vision.append(
                re.search("[（(\[【 ]\d{1,2}((v\d)((版本?|修复?正?版?)|片源?|内详)?)[）)\]】]", str(file_name)).group(1))
        except Exception as e:
            logging.info(e)
        # [v2]
        try:
            vision.append(
                re.search("[（(\[【 ](v\d)[）)\]】]", str(file_name)).group(1))
        except Exception as e:
            logging.info(e)
        if vision:
            return vision
        else:
            return None

    # 获取字幕类型
    def get_ass(self):
        file_name = self.file_name.lower()
        ass = []
        # 中文标示
        try:
            ass.append(
                re.search("[（(\[【]?(附?([内外][挂嵌封]\+?){1,2}(字幕)?)[）)\]】]?", str(file_name)).group(1))
        except Exception as e:
            logging.info(e)
        # 英文标示
        try:
            ass.append(
                re.search("[（(\[【]?(([ +]?(ass|pgs|srt)){1,3})[）)\]】]?", str(file_name)).group(1).strip(" "))
        except Exception as e:
            logging.info(e)
        if ass:
            return ass
        else:
            return None

    def has_en(self, str):
        my_re = re.compile(r'[a-z]', re.S)
        res = re.findall(my_re, str)
        if len(res):
            return True
        else:
            return False

    def has_zh(self, str):
        my_re = re.compile(r'[\u4e00-\u9fa5]', re.S)
        res = re.findall(my_re, str)
        if len(res):
            return True
        else:
            return False

    def extract_title(self, raw_name):
        title = {
            "zh": None,
            "en": None,
        }

        clean_name = raw_name
        if self.has_en(clean_name) and self.has_zh(clean_name):
            # 中英
            try:
                res = re.search("(([\u4e00-\u9fa5]{2,12}[ /:]{0,3}){1,5}) {0,5}(( ?[a-z':]{1,15}){1,15})", clean_name)
                title["zh"] = res.group(1).strip(" ")
                title["en"] = res.group(3).strip(" ")
            except Exception as e:
                logging.info(e)
            # 本程序依赖此bug运行，这行不能删
            if title["zh"] is None:
                # 中英
                try:
                    res = re.search(
                        "(([\u4e00-\u9fa5a]{1,12}[ /:]{0,3}){1,5})[&/ (]{0,5}(( ?[a-z':]{1,15}){1,15})[ )/]{0,3}",
                        clean_name)
                    title["zh"] = res.group(1).strip(" ")
                    title["en"] = res.group(3).strip(" ")
                except Exception as e:
                    logging.info(e)
                # 英中
                try:
                    res = re.search(
                        "(([ a-z'.:]{1,20}){1,8})[&/ (]{0,5}(([\u4e00-\u9fa5a]{2,10}[a-z]{0,3} ?){1,5})[ )/]{0,3}",
                        clean_name)
                    title["en"] = res.group(1).strip(" ")
                    title["zh"] = res.group(3).strip(" ")
                except Exception as e:
                    logging.info(e)
        else:
            if self.has_zh(clean_name):
                # 中文
                try:
                    res = re.search("(([\u4e00-\u9fa5:]{2,15}[ /]?){1,5}) *", clean_name)
                    title["zh"] = res.group(1).strip(" ")
                except Exception as e:
                    logging.info(e)
            elif self.has_en(clean_name):
                # 英文
                try:
                    res = re.search("(([a-z:]{2,15}[ /]?){1,15}) *", clean_name)
                    title["en"] = res.group(1).strip(" ")
                except Exception as e:
                    logging.info(e)
        for k, v in title.items():
            if v is not None and "/" in v:
                zh_list = v.split("/")
                title[k] = zh_list[0].strip(" ")
        return title

    def add_separator(self, clean_name):
        if "/" not in clean_name:
            if '\u4e00' <= clean_name[0] <= '\u9fff':
                try:
                    res = re.search("(^[a\u4e00-\u9fa5: ]{1,10} ?)([a-z:]{1,20} ?){1,10}", clean_name).group(1)
                    clean_name = clean_name.replace(res, res.strip(" ") + "/")
                    print("zh_pre:%s" % clean_name)
                except Exception as e:
                    print(e)
            else:
                try:
                    res = re.search("^(([a-z:]{1,20} ?){1,10} )[\u4e00-\u9fa5: a]{1,20}", clean_name).group(1)
                    clean_name = clean_name.replace(res, res.strip(" ") + "/")
                    print("en_pre:%s" % clean_name)
                except Exception as e:
                    print(e)
        return clean_name

    def easy_split(self, clean_name, zh_list, en_list):
        if "/" in clean_name:
            n_list = clean_name.split("/")
            for i in n_list:
                if self.has_zh(i) is False:
                    en_list.append(i.strip(" "))
                elif self.has_en(i) is False:
                    zh_list.append(i.strip(" "))
                else:
                    # 如果还是同时包含中英文的情况，递龟一下
                    i = self.add_separator(i)
                    self.easy_split(i, zh_list, en_list)
        else:
            if self.has_zh(clean_name) is False:
                en_list.append(clean_name.strip(" "))
            elif self.has_en(clean_name) is False:
                zh_list.append(clean_name.strip(" "))

    # 拿到的数据挨个测试
    def get_info(self):
        # 获取到的信息
        info = {
            "group": self.get_group(),
            "dpi": self.get_dpi(),
            "season": self.get_season(),
            "episode": self.get_episode(),
            "vision": self.get_vision(),
            "lang": self.get_language(),
            "ass": self.get_ass(),
            "type": self.get_type(),
            "code": self.get_code(),
            "source": self.get_source()
        }

        # 字母全部小写
        clean_name = self.file_name.lower()
        # 去除拿到的有效信息
        for k, v in info.items():
            if v is not None:
                if type(v) is list:
                    for i in v:
                        clean_name = clean_name.replace(i, "") if i is not None else clean_name
                else:
                    clean_name = clean_name.replace(v, "")
        # 除杂
        clean_list = ["pc&psp", "pc&psv", "fin", "opus", "movie", "tvb", "end", "web", "bangumi.online", "donghua",
                      "话全", "第话", "第集", "全集", "话", "集", "+", "@", "轨", "。"]
        for i in clean_list:
            clean_name = clean_name.replace(i, "")
        # 去除多余空格
        clean_name = re.sub(' +', ' ', clean_name).strip(" ")
        # 分隔各字段
        clean_name = re.sub("([(\[] *| *[)\]])", "", clean_name)

        # 剩下来的几乎就是干净番名了，再刮不到不管了
        info["clean_name"] = clean_name
        clean_name = re.sub('[^a-zA-Z\u4e00-\u9fa5:@#$%^&*()\[\]/ ]', "", clean_name)
        clean_name = re.sub(' +', ' ', clean_name).strip(" ")
        clean_name = re.sub("([(\[] *| *[)\]])", "", clean_name)
        print(clean_name)

        title = {
            "zh": None,
            "en": None
        }
        zh_list = []
        en_list = []
        clean_name = self.add_separator(clean_name)
        self.easy_split(clean_name, zh_list, en_list)
        title["zh"] = zh_list if zh_list else None
        title["en"] = en_list if en_list else None
        if title["zh"] is None and title["en"] is None:
            title = self.extract_title(clean_name)
        print(title)
        info["title"] = title
        return info


if __name__ == "__main__":
    raw = ChainDb("spider_dmhy").page(1, 1000).field("name").select()
    name_list = [x["name"] for x in raw]
    start = time.time()
    for name in name_list:
        print(name)
        Rename(name).get_info()
        print()
    print("%s" % (time.time() - start))
