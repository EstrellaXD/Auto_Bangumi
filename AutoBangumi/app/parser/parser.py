import re
import requests



class Parser:
    # TODO 番剧名称识别
    def __init__(self, info):
        self.raw_name = info
        self.name = None
        self.season = None
        self.episode = None
        self.group = None
        self.dpi = None
        self.language = None
        try:
            self.rules = requests.get(settings.rule_url).json()
        except Exception as e:
            logger.exception(e)
        json_config.save(settings.rule_path, self.rules)

    # 第一类字幕组分类
    def parser_type_1(self):
        name_re_group = re.sub(r"^[^(\]|】)]*(\]|】)", "", self.raw_name).strip()
        match_obj = re.match(r"(.*|\[.*])( - \d{1,3}|\[\d{1,3}])(.*)", name_re_group)
        name_season = match_obj.group(1).strip()
        if re.search(r"S\d{1,2}", name_season) is not None:
            split = re.sub(r"S\d{1,2}", "", name_season).split("/")
            self.season = re.findall(r"S\d{1,2}", name_season)[0]
        else:
            split = name_season.split("/")
            self.season = "S01"
        try:
            self.name = split[1].strip()
        except IndexError:
            self.name = split[-1].strip()
        self.episode = int(re.sub(r"\-|\[|\]", "", match_obj.group(2)))
        other = match_obj.group(3).strip()
        language = None

    def parser_type_2(self):
        self.name = "name"

    def parser_type_3(self):
        self.name = "name"

    def method(self, method):
        if method == 1:
            self.parser_type_1()
        elif method == 2:
            self.parser_type_2()
        elif method == 3:
            self.parser_type_3()

    def split_info(self):
        break_flag = False
        for rule in self.rules:
            for group in rule["group"]:
                if re.search(group, self.raw_name):
                    self.method(rule["type"])
                    self.group = group
                    break_flag = True
                    break
            if break_flag:
                break

