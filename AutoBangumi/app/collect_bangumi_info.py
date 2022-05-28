# -*- coding: UTF-8 -*-
import sys
import requests
from bs4 import BeautifulSoup
import json
import re
from env import EnvInfo, BColors
from RSSFilter import RSSInfoCleaner as Filter

class MatchRule:
    split_rule = r"\[|\]|\【|\】|\★|\（|\）|\(|\)"
    last_rule = r"(.*)( \-)"
    sub_title = r"[^\x00-\xff]{1,}| \d{1,2}^.*|\·"
    match_rule = r"(S\d{1,2}(.*))"
    season_match = r"(.*)(Season \d{1,2}|S\d{1,2}|第.*季|第.*期)"


class CollectRSS:
    def __init__(self):
        self.bangumi_list = []
        with open(EnvInfo.rule_path) as r:
            self.rules = json.load(r)
        try:
            self.rules = requests.get(EnvInfo.rule_url).json()
            with open(EnvInfo.rule_path, 'w') as f:
                json.dump(self.rules, f, indent=4, separators=(',', ': '), ensure_ascii=False)
        except:
            with open(EnvInfo.rule_path) as r:
                self.rules = json.load(r)
        rss = requests.get(EnvInfo.rss_link, 'utf-8')
        soup = BeautifulSoup(rss.text, 'xml')
        self.items = soup.find_all('item')
        with open(EnvInfo.info_path) as i:
            self.info = json.load(i)

    def get_info_list(self):
        for item in self.items:
            name = item.title.string
            # debug 用
            if EnvInfo.get_rule_debug:
                sys.stdout.write(f"[{EnvInfo.time_show_obj}]  Raw {name}")
            exit_flag = False
            for rule in self.rules:
                for group in rule["group_name"]:
                    if re.search(group, name):
                        exit_flag = True
                        n = re.split(MatchRule.split_rule, name)
                        while '' in n:
                            n.remove('')
                        while ' ' in n:
                            n.remove(' ')
                        try:
                            bangumi_title = n[rule['name_position']].strip()
                        except IndexError:
                            continue
                        sub_title = re.sub(MatchRule.sub_title, "", bangumi_title)
                        b = re.split(r"\/|\_", sub_title)
                        while '' in b:
                            b.remove('')
                        pre_name = max(b, key=len, default='').strip()
                        if len(pre_name.encode()) > 3:
                            bangumi_title = pre_name
                        for i in range(2):
                            match_obj = re.match(MatchRule.last_rule, bangumi_title, re.I)
                            if match_obj is not None:
                                bangumi_title = match_obj.group(1).strip()
                        match_obj = re.match(MatchRule.match_rule, bangumi_title, re.I)
                        if match_obj is not None:
                            bangumi_title = match_obj.group(2).strip()
                        if bangumi_title not in self.bangumi_list:
                            self.bangumi_list.append({
                                "title": bangumi_title,
                                "group": group
                            })
                        # debug
                        # print(bangumi_title)
                        # print(group)
                        break
                if exit_flag:
                    break
            if not exit_flag:
                sys.stdout.write(f"[{EnvInfo.time_show_obj}]  ERROR Not match with {name}")

    def put_info_json(self):
        had_data = []
        if self.info["rss_link"] == EnvInfo.rss_link:
            for data in self.info["bangumi_info"]:
                had_data.append(data["title"])
        else:
            self.info = {
                "rss_link": EnvInfo.rss_link,
                "bangumi_info": []
            }
        for item in self.bangumi_list:
            match_title_season = re.match(MatchRule.season_match, item["title"], re.I)
            if match_title_season is not None:
                json_title = match_title_season.group(1).strip()
                json_season = match_title_season.group(2)
            else:
                json_season = 'S01'
                json_title = item["title"]
            if json_title not in had_data:
                self.info["bangumi_info"].append({
                    "title": json_title,
                    "season": json_season,
                    "group": item["group"],
                    "added": False
                })
                had_data.append(json_title)
                sys.stdout.write(f"[{EnvInfo.time_show_obj}]  add {json_title} {json_season}" + "\n")
                sys.stdout.flush()
        with open(EnvInfo.info_path, 'w', encoding='utf8') as f:
            json.dump(self.info, f, indent=4, separators=(',', ': '), ensure_ascii=False)

    def run(self):
        self.get_info_list()
        self.put_info_json()


if __name__ == "__main__":
    rss = requests.get(EnvInfo.rss_link, 'utf-8')
    soup = BeautifulSoup(rss.text, 'xml')
    items = soup.find_all('item')
    for item in items:
        name = item.title.string
        print(BColors.HEADER + name + BColors.OKGREEN)
        pn = Filter(name).Name
        print(pn.clean)

        # print(BColors.HEADER + name)
        # print(BColors.OKGREEN + str(pn.Name.en))