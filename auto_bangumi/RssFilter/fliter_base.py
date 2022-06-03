import re
import logging

import csv

logger = logging.getLogger(__name__)

def read_data(file_name, start, rows):
    if file_name == "mikan":
        with open('RssFilter/mikan.csv', 'r', encoding='utf-8') as csv_file:
            reader = csv.reader(csv_file)
            raw_data = [row[3] for row in reader][start:start + rows]
            return raw_data
    elif file_name == "dmhy":
        with open('RssFilter/dmhy.csv', 'r', encoding='utf-8') as csv_file:
            reader = csv.reader(csv_file)
            raw_data = [row[4] for row in reader][start + 1:start + rows + 1]
            return raw_data


# 以 / 代替空格分隔中英文名
def add_separator(clean_name):
    try:
        if '\u4e00' <= clean_name[0] <= '\u9fff':
            try:
                res = re.search(
                    "(^[\u4e00-\u9fa5\u3040-\u31ff\d: \-·、.。，!！]{1,20}[ -_]{1,5})([a-z\d:\-.。,，!！]{1,20} ?){2,}",
                    clean_name).group(1)
                clean_name = clean_name.replace(res, res.strip(" ") + "/")
            except Exception as e:
                logger.exception(e)
        else:
            try:
                res = re.search(
                    "^(([a-z\d:\-.。,，!！]{1,20} ?){2,}[ -_]{1,5})[\u4e00-\u9fa5\u3040-\u31ff\d: \-·、.。,，!！]{1,20}",
                    clean_name).group(1)
                clean_name = clean_name.replace(res, res.strip(" ") + "/")
            except Exception as e:
                logger.exception(e)
    except Exception as e:
        logger.exception(e)
    clean_name = re.sub("(/ */)", "/", clean_name)
    return clean_name


# 拼合碎片
def splicing(frag_list, name_list, raw_name):
    try:
        for i in range(0, len(name_list) - 1):
            if name_list[i] in name_list[i + 1] and name_list[i] != name_list[i + 1]:
                name_list.remove(name_list[i])
            elif name_list[i + 1] in name_list[i] and name_list[i] != name_list[i + 1]:
                name_list.remove(name_list[i + 1])
    except Exception as e:
        logger.info(e)
    min_list = sorted(name_list, key=lambda i: len(i), reverse=False)
    for i in range(0, len(min_list) - 1):
        # 处理中英文混合名
        if frag_list is not None and len(frag_list) > 1:
            fragment = min_list[i]
            try:
                if fragment in raw_name.lower():
                    for piece_name in name_list:
                        try:
                            r_name = re.search("(%s {0,3}%s|%s {0,5}%s)" % (fragment, piece_name, piece_name, fragment),
                                               raw_name.lower())
                            if r_name is not None:
                                frag_list.remove(fragment)
                                name_list.remove(piece_name)
                                name_list.append(r_name.group())
                        except Exception as e:
                            logger.warning("bug--%s" % e)
                            logger.warning("piece_name:%s,fragment:%s" % (piece_name, fragment))
            except Exception as e:
                logger.exception(e)


# 清理列表
def clean_list(raw_list):
    if raw_list is not None:
        # 去除碎片和杂质
        raw_list = [x.strip("-").strip(" ") for x in raw_list if len(x) > 1]
        # 小碎片归并
        for _ in range(len(raw_list)):
            if raw_list is not None and len(raw_list) > 1:
                try:
                    for i in range(0, len(raw_list) - 1):
                        if raw_list[i] in raw_list[i + 1] and raw_list[i] != raw_list[i + 1]:
                            raw_list.remove(raw_list[i])
                        elif raw_list[i + 1] in raw_list[i] and raw_list[i] != raw_list[i + 1]:
                            raw_list.remove(raw_list[i + 1])
                except Exception as e:
                    logger.info(e)
            if raw_list is not None and len(raw_list) > 1:
                try:
                    for i in range(0, len(raw_list)):
                        up_list = sorted(raw_list, key=lambda i: len(i), reverse=False)
                        if up_list[i] in up_list[-1] and up_list[i] != up_list[-1]:
                            raw_list.remove(up_list[i])
                except Exception as e:
                    logger.info(e)
    if raw_list:
        return set(raw_list)
    else:
        return None


# 粗略识别失败，re强制匹配
def extract_title(raw_name):
    title = {
        "zh": None,
        "en": None,
    }
    clean_name = raw_name

    if has_en(clean_name) and has_zh(clean_name):
        # 中英
        try:
            res = re.search("(([\u4e00-\u9fa5]{2,12}[ /:]{0,3}){1,5}) {0,5}(( ?[a-z':]{1,15}){1,15})", clean_name)
            title["zh"] = res.group(1).strip(" ")
            title["en"] = res.group(3).strip(" ")
        except Exception as e:
            logger.info(e)
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
                logger.info(e)
            # 英中
            try:
                res = re.search(
                    "(([ a-z'.:]{1,20}){1,8})[&/ (]{0,5}(([\u4e00-\u9fa5a]{2,10}[a-z]{0,3} ?){1,5})[ )/]{0,3}",
                    clean_name)
                title["en"] = res.group(1).strip(" ")
                title["zh"] = res.group(3).strip(" ")
            except Exception as e:
                logger.info(e)
    else:
        if has_zh(clean_name):
            # 中文
            try:
                res = re.search("(([\u4e00-\u9fa5:]{2,15}[ /]?){1,5}) *", clean_name)
                title["zh"] = res.group(1).strip(" ")
            except Exception as e:
                logger.info(e)
        elif has_en(clean_name):
            # 英文
            try:
                res = re.search("(([a-z:]{2,15}[ /]?){1,15}) *", clean_name)
                title["en"] = res.group(1).strip(" ")
            except Exception as e:
                logger.info(e)
    for k, v in title.items():
        if v is not None and "/" in v:
            zh_list = v.split("/")
            title[k] = zh_list[0].strip(" ")
    return title


def del_rules(raw_name, rule_list):
    for i in rule_list:
        raw_name = raw_name.replace(i, "")
    return raw_name


# 获取字符串出现位置
def get_str_location(char, target):
    locate = []
    for index, value in enumerate(char):
        if target == value:
            locate.append(index)
    return locate


# 匹配某字符串最近的括号
def get_gp(char, string):
    begin = [x for x in get_str_location(string, "[") if int(x) < int(string.find(char))][-1] + 1
    end = [x for x in get_str_location(string, "]") if int(x) > int(string.find(char))][0]
    return string[begin:end]


def has_en(str):
    my_re = re.compile(r'[a-z]', re.S)
    res = re.findall(my_re, str)
    if len(res):
        return True
    else:
        return False


def has_zh(str):
    my_re = re.compile(r'[\u4e00-\u9fa5]', re.S)
    res = re.findall(my_re, str)
    if len(res):
        return True
    else:
        return False


def has_jp(str):
    my_re = re.compile(r'[\u3040-\u31ff]', re.S)
    res = re.findall(my_re, str)
    if len(res):
        return True
    else:
        return False


# 单list验证
def re_verity(raw_list, raw_name):
    correct_list = []
    for c_res in raw_list:
        if type(raw_name) is list:
            if c_res in raw_name[0].lower() and c_res in raw_name[1].lower():
                correct_list.append(c_res)
        else:
            if c_res in raw_name.lower():
                correct_list.append(c_res)
    return correct_list
