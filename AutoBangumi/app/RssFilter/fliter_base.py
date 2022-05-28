import re
import logging

import csv


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
        if "/" not in clean_name:
            if '\u4e00' <= clean_name[0] <= '\u9fff':
                try:
                    res = re.search(
                        "(^[\u4e00-\u9fa5\u3040-\u31ff: \-.。，!！]{1,20}[ -]{0,5})([a-z: \-.。,，!！]{1,20} ?)*",
                        clean_name).group(1)
                    clean_name = clean_name.replace(res, res.strip(" ") + "/")
                except Exception as e:
                    logging.info(e)
            else:
                try:
                    res = re.search(
                        "^(([a-z: \-.。,，!！]{1,20} ?)*[ -]{0,5})[\u4e00-\u9fa5\u3040-\u31ff: \-.。,，!！]{1,20}",
                        clean_name).group(1)
                    clean_name = clean_name.replace(res, res.strip(" ") + "/")
                except Exception as e:
                    logging.info(e)
    except Exception as e:
        logging.info(e)
    return clean_name


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
