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
bangumi_title = ''
for item in items:
    name = item.title.string
    bangumi_title = ''
    print(name)
    exit_flag = False
    for rule in rules:
        for group in rule["group_name"]:
            if re.search(group, name):
                exit_flag = True
                n = re.split(split_rule, name)
                for i in rule["name_position"]:
                    bangumi_title = bangumi_title + ' ' + n[i].strip()
                print(bangumi_title)
                break
        if exit_flag:
            break