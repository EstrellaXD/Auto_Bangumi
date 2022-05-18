import re

import requests
from bs4 import BeautifulSoup
import json

url = "https://mikanani.me/RSS/Classic"
rss = requests.get(url, 'utf-8')
soup = BeautifulSoup(rss.text, 'xml')
items = soup.find_all('item')
with open("rule.json") as f:
    rules = json.load(f)
split_rule = r"\[|\]|\【|\】|\★|\（|\）|\(|\)"
bangumi_list = []
bangumi_title = ''
for item in items:
    name = item.title.string
    bangumi_title = ''
    exit_flag = False
    for rule in rules:
        for group in rule["group_name"]:
            if re.search(group, name):
                exit_flag = True
                n = re.split(split_rule, name)
                while '' in n:
                    n.remove('')
                for i in rule["name_position"]:
                    bangumi_title = bangumi_title + ' ' + n[i].strip()
                if bangumi_title not in bangumi_list:
                    bangumi_list.append(bangumi_title)
                break
        if exit_flag:
            break
season_rule = r"Season \d{1,2}|S\d{1,2}|第.*季|.*期"
episode_rule = r"\d{1,2}|第\d{1,2}话"
for item in bangumi_list:
    season = re.findall(season_rule, item)
    title = re.sub(season_rule, '', item)
    try:
        season = season[-1]
    except IndexError:
        season = ""
    episode = re.findall(episode_rule, title)
    try:
        episode = episode[-1]
    except IndexError:
        episode = ""
    title = re.sub(episode_rule, '', title)
    t = re.split(r"/|_", title)
    while "" in t:
        t.remove("")
    name = t[-1].strip()
    print(name)
    print(season)
    print(episode)

print(bangumi_list)