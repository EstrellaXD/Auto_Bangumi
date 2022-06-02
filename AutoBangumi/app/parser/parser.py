import re
from conf import settings
from utils import json_config
import requests
from log import logger



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

    def parser_type_1(self):

        self.name = "name"
        self.season = "S01"
        self.episode = 1
        self.dpi = "1080p"
        self.language = "CHT"


    def parser_type_2(self):
        self.name = "name"

    def method(self, method):
        if method == 1:
            self.parser_type_1()
        elif method == 2:
            self.parser_type_2()
        elif method == 3:



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

