# -*- coding: UTF-8 -*-
import sys
import time
import requests
from bs4 import BeautifulSoup
import json
import re


class CollectRSS:
    def __init__(self, config, info):
        self.bangumi_list = []
        with open("/app/rule.json") as f:
            self.rules = json.load(f)
        rss = requests.get(config["rss_link"], 'utf-8')
        soup = BeautifulSoup(rss.text, 'xml')
        self.items = soup.find_all('item')
        self.info = info

    def get_info_list(self):
        split_rule = r"\[|\]|\【|\】|\★|\（|\）|\(|\)"
        last_rule = r"(.*)( \-)"
        for item in self.items:
            name = item.title.string
            exit_flag = False
            for rule in self.rules:
                for group in rule["group_name"]:
                    if re.search(group, name):
                        exit_flag = True
                        n = re.split(split_rule, name)
                        while '' in n:
                            n.remove('')
                        while ' ' in n:
                            n.remove(' ')
                        try:
                            bangumi_title = n[rule['name_position']].strip()
                        except IndexError:
                            continue
                        sub_title = re.sub(r"[^\x00-\xff]{1,}| \d{1,2}|\·","",bangumi_title)
                        b = re.split(r"\/|\_", sub_title)
                        while '' in b:
                            b.remove('')
                        pre_name = max(b, key=len, default='').strip()
                        if pre_name != '':
                            bangumi_title = pre_name
                        for i in range(2):
                            match_obj = re.match(last_rule, bangumi_title, re.I)
                            if match_obj is not None:
                                bangumi_title = match_obj.group(1).strip()
                        match_obj = re.match(r"(S\d{1,2}(.*))", bangumi_title, re.I)
                        if match_obj is not None:
                            bangumi_title = match_obj.group(2).strip()
                        if bangumi_title not in self.bangumi_list:
                            self.bangumi_list.append(bangumi_title)
                        break
                if exit_flag:
                    break
            if not exit_flag:
                print(f"ERROR Not match with {name}")

    def put_info_json(self):
        season_match = r"(.*)(Season \d{1,2}|S\d{1,2}|第.*季)"

        had_data = []
        for data in self.info:
            had_data.append(data["title"])

        for title in self.bangumi_list:
            match_title_season = re.match(season_match, title, re.I)
            if match_title_season is not None:
                json_title = match_title_season.group(1).strip()
                json_season = match_title_season.group(2)
            else:
                json_season = ''
                json_title = title
            if json_title not in had_data:
                self.info.append({
                    "title": json_title,
                    "season": json_season
                })
                sys.stdout.write(f"[{time.strftime('%Y-%m-%d %X')}]  add {json_title} {json_season}" + "\n")
                sys.stdout.flush()
        with open("/config/bangumi.json", 'w', encoding='utf8') as f:
            json.dump(self.info, f, indent=4, separators=(',', ': '), ensure_ascii=False)

    def run(self):
        self.get_info_list()
        self.put_info_json()