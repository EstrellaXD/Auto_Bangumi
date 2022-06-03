import re
import logging
import requests
from conf import settings
from utils import json_config

from bangumi_parser.episode import Episode

logger = logging.getLogger(__name__)


class MatchRule:
    split_rule = r"\[|\]|\【|\】|\★|\（|\）|\(|\)"
    last_rule = r"(.*)( \-)"
    sub_title = r"[^\x00-\xff]{1,}| \d{1,2}^.*|\·"
    match_rule = r"(S\d{1,2}(.*))"
    season_match = r"(.*)(Season \d{1,2}|S\d{1,2}|第.*季|第.*期)"
    season_number_match = r"(\d+)"


# 简单往往是最好的
class SimpleAnalyser:
    def __init__(self) -> None:
        self.rules = json_config.load(settings.rule_path)
        try:
            self.rules = requests.get(settings.rule_url).json()
            json_config.save(settings.rule_path, self.rules)
        except Exception as e:
            logger.exception(e)

    def analyse(self, name) -> Episode:
        flag = False
        for rule in self.rules:
            for group in rule["group_name"]:
                if re.search(group, name):
                    n = re.split(MatchRule.split_rule, name)
                    while "" in n:
                        n.remove("")
                    while " " in n:
                        n.remove(" ")
                    try:
                        title = n[rule["name_position"]].strip()
                    except IndexError:
                        continue
                    sub_title = re.sub(MatchRule.sub_title, "", title)
                    b = re.split(r"\/|\_", sub_title)
                    while "" in b:
                        b.remove("")
                    pre_name = max(b, key=len, default="").strip()
                    if len(pre_name.encode()) > 3:
                        title = pre_name
                    for i in range(2):
                        match_obj = re.match(MatchRule.last_rule, title, re.I)
                        if match_obj is not None:
                            title = match_obj.group(1).strip()
                    match_obj = re.match(MatchRule.match_rule, title, re.I)
                    if match_obj is not None:
                        title = match_obj.group(2).strip()
                    # debug
                    # print(bangumi_title)
                    # print(group)
                    flag = True
                    break
            if flag:
                break
        if not flag:
            logger.debug("ERROR Not match with {name}")
            return
        match_title_season = re.match(MatchRule.season_match, title, re.I)
        if match_title_season is not None:
            title = match_title_season.group(1).strip()
            season = match_title_season.group(2)
            match_season_number = re.findall(MatchRule.season_number_match, season)
            try:
                season_number = int(match_season_number[0])
            except:
                logger.warning(
                    f"title:{title} season:{season} can't match season in number"
                )
            finally:
                season_number = 1
        else:
            season = "S01"
            season_number = 1
        episode = Episode()
        episode.title = title
        episode.group = group
        episode.season_info.raw = season
        episode.season_info.number = season_number
        return episode
