# -*- coding: UTF-8 -*-
import os
import logging
import requests
from bs4 import BeautifulSoup
import json
import re
from conf import settings
from utils import json_config

# from RssFilter.RSSFilter import RSSInfoCleaner as Filter

logger = logging.getLogger(__name__)


class MatchRule:
    split_rule = r"\[|\]|\【|\】|\★|\（|\）|\(|\)"
    last_rule = r"(.*)( \-)"
    sub_title = r"[^\x00-\xff]{1,}| \d{1,2}^.*|\·"
    match_rule = r"(S\d{1,2}(.*))"
    season_match = r"(.*)(Season \d{1,2}|S\d{1,2}|第.*季|第.*期)"
    season_number_match = r"(\d+)"


class CollectRSS:
    def __init__(self):
        self.bangumi_list = []
        self.rules = json_config.load(settings.rule_path)
        try:
            self.rules = requests.get(settings.rule_url).json()
        except Exception as e:
            logger.exception(e)
        json_config.save(settings.rule_path, self.rules)
        try:
            rss = requests.get(settings.rss_link, "utf-8")
        except Exception as e:
            logger.exception(e)
            logger.error("ERROR with DNS/Connection.")
            quit()
        soup = BeautifulSoup(rss.text, "xml")
        self.items = soup.find_all("item")
        self.info = json_config.load(settings.info_path)

    def get_info_list(self):
        for item in self.items:
            name = item.title.string
            # debug 用
            if settings.get_rule_debug:
                logger.debug(f"Raw {name}")
            exit_flag = False
            for rule in self.rules:
                for group in rule["group_name"]:
                    if re.search(group, name):
                        exit_flag = True
                        n = re.split(MatchRule.split_rule, name)
                        while "" in n:
                            n.remove("")
                        while " " in n:
                            n.remove(" ")
                        try:
                            bangumi_title = n[rule["name_position"]].strip()
                        except IndexError:
                            continue
                        sub_title = re.sub(MatchRule.sub_title, "", bangumi_title)
                        b = re.split(r"\/|\_", sub_title)
                        while "" in b:
                            b.remove("")
                        pre_name = max(b, key=len, default="").strip()
                        if len(pre_name.encode()) > 3:
                            bangumi_title = pre_name
                        for i in range(2):
                            match_obj = re.match(
                                MatchRule.last_rule, bangumi_title, re.I
                            )
                            if match_obj is not None:
                                bangumi_title = match_obj.group(1).strip()
                        match_obj = re.match(MatchRule.match_rule, bangumi_title, re.I)
                        if match_obj is not None:
                            bangumi_title = match_obj.group(2).strip()
                        if bangumi_title not in self.bangumi_list:
                            self.bangumi_list.append(
                                {"title": bangumi_title, "group": group}
                            )
                        # debug
                        # print(bangumi_title)
                        # print(group)
                        break
                if exit_flag:
                    break
            if not exit_flag:
                logger.debug("ERROR Not match with {name}")

    def put_info_json(self):
        had_data = []
        if self.info["rss_link"] == settings.rss_link:
            for data in self.info["bangumi_info"]:
                had_data.append(data["title"])
        else:
            self.info = {"rss_link": settings.rss_link, "bangumi_info": []}
        for item in self.bangumi_list:
            title = item["title"]
            match_title_season = re.match(MatchRule.season_match, title, re.I)
            if match_title_season is not None:
                json_title = match_title_season.group(1).strip()
                json_season = match_title_season.group(2)
                match_season_number = re.findall(
                    MatchRule.season_number_match, json_season
                )
                if len(match_season_number) != 0:
                    json_season_number = int(match_season_number[0])
                else:
                    logger.warning(
                        f"title:{title} season:{json_season} can't match season in number"
                    )
                    json_season_number = 1
            else:
                json_season = "S01"
                json_season_number = 1
                json_title = title
            if json_title not in had_data:
                self.info["bangumi_info"].append(
                    {
                        "title": json_title,
                        "season": json_season,
                        "season_number": json_season_number,
                        "group": item["group"],
                        "added": False,
                    }
                )
                had_data.append(json_title)
                logger.debug("add {json_title} {json_season}")
        json_config.save(settings.info_path, self.info)

    def run(self):
        self.get_info_list()
        self.put_info_json()


if __name__ == "__main__":
    # from const import BCOLORS
    # rss = requests.get(settings.rss_link, 'utf-8')
    # soup = BeautifulSoup(rss.text, 'xml')
    # items = soup.find_all('item')
    # for item in items:
    #     name = item.title.string
    #     pn = Filter(name).Name
    #     print(BCOLORS.HEADER + name)
    #     print(BCOLORS.OKGREEN + str(pn.zh))
    #     print(str(pn.en))
    print(__file__)
    print(os.path.dirname(__file__))
