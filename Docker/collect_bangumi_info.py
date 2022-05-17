# -*- coding: UTF-8 -*-
import requests
from bs4 import BeautifulSoup
import json
import re


def collect_info():
    episode_rules = [r'(.*)\[(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)',
                     r'(.*)\[E(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)',
                     r'(.*)\[第(\d*\.*\d*)话(?:END)?\](.*)',
                     r'(.*)\[第(\d*\.*\d*)話(?:END)?\](.*)',
                     r'(.*)第(\d*\.*\d*)话(?:END)?(.*)',
                     r'(.*)第(\d*\.*\d*)話(?:END)?(.*)',
                     r'(.*)- (\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)? (.*)']
    with open('./config/config.json') as f:
        config = json.load(f)
    url = config["rss_link"]
    rss = requests.get(url, 'utf-8')
    soup = BeautifulSoup(rss.text, 'xml')
    item = soup.find_all('item')
    bangumi_title = []
    for a in item:
        name = str(a.find('title'))
        name = re.sub('<title>|</title>', '', name)
        parrten = r'\[|\]|\u3010|\u3011|\★|\*'
        symbol = [['[', ']'], ['【', '】'], ['★', '★']]
        for i in range(2):
            n = re.split(parrten, name)
            name = re.sub(f'\[{n[1]}\]|【{n[1]}】|★{n[1]}★', '', name)
        for rule in episode_rules:
            matchObj = re.match(rule, name, re.I)
            if matchObj is not None:
                new_name = re.sub(r'\[|\]', '', f'{matchObj.group(1)}')
                new_name = re.split(r'/', new_name)[-1].strip()
                if new_name not in bangumi_title:
                    bangumi_title.append(new_name)

    with open("./data/bangumi.json", encoding='utf-8') as f:
        bangumi_info = json.load(f)
    had_data = []
    for data in bangumi_info:
        had_data.append(data["title"])

    season_rules = r'(.*)(S.\d)'
    for title in bangumi_title:
        a = re.match(season_rules, title, re.I)
        if a is not None:
            title = a.group(1).strip()
            season = a.group(2).strip()
        else:
            season = ''
        if title not in had_data:
            bangumi_info.append({
                "title": title,
                "season": season
            })
            print(f"add {title} {season}")
    # 写入数据
    with open("./data/bangumi.json", 'w', encoding='utf8') as f:
        json.dump(bangumi_info, f, indent=4, separators=(',', ': '), ensure_ascii=False)