import re

import requests
from bs4 import BeautifulSoup



episode_rules = [r'(.*)\[(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)',
                         r'(.*)\[E(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)',
                         r'(.*)\[第(\d*\.*\d*)话(?:END)?\](.*)',
                         r'(.*)\[第(\d*\.*\d*)話(?:END)?\](.*)',
                         r'(.*)第(\d*\.*\d*)话(?:END)?(.*)',
                         r'(.*)第(\d*\.*\d*)話(?:END)?(.*)',
                         r'(.*)- (\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)? (.*)']


name = "[NC-Raws] 小书痴的下克上：为了成为图书管理员不择手段！第三季 / Honzuki no Gekokujou S3 - 32 (Baha 1920x1080 AVC AAC MP4)"
parrten = r'\[|\]|\u3010|\u3011|\★|\*|\(|\)|\（|\）'
for i in range(2):
    n = re.split(parrten, name)
    try:
        name = re.sub(f'\[{n[1]}\]|【{n[1]}】|★{n[1]}★', '', name)
    except:
        name = name
for rule in episode_rules:
    matchObj = re.match(rule, name, re.I)
    if matchObj is not None:
        new_name = re.sub(r'\[|\]', '', f'{matchObj.group(1)}')
        new_name = re.split(r'/', new_name)[-1].strip()
        print(new_name)
