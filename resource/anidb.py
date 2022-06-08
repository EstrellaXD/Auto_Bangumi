#! /usr/bin/python
import re
import time

import requests
from bs4 import BeautifulSoup
from utils import json_config
from const import BCOLORS

header = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ApplewebKit/537.36 (KHtml, like Gecko) Chrome/80.0.3987.163 Safari/537.36',
}


def get_html(url):
    requests.adapters.DEFAULT_RETRIES = 5  # 增加重连次数
    s = requests.session()
    s.keep_alive = False  # 关闭多余连接
    html = s.get(url=url, headers=header).text
    print("get html success")
    return html


def get_list(year, season):
    season = ["spring", "summer", "autumn", "winter"][season - 1]
    url = "https://anidb.net/anime/season/%s/%s/" % (year, season)
    html = get_html(url)
    ids = re.findall("<a href=\"/anime/(\d+)\"><picture>", html)
    return ids


def get_title_legecy(id):
    url = "https://anidb.net/anime/%s" % id
    soup = BeautifulSoup(get_html(url), "lxml")
    titles = soup.find("div", id="tab_2_pane")
    g = titles.findAll("th")
    v = titles.findAll("td")
    t_dic = {
        "id": id,
        "main": None,
        "verified": None,
        "en": None,
        "chs": None,
        "cht": None,
        "jp": None,
        "synonym": None,
        "kana": None
    }
    for i in range(0, len(g)):
        if g[i].text == "Main Title":
            t_dic["main"] = re.sub("\(a\d+\)", "", v[i].text).strip("\n\t")
        elif g[i].text == "Official Title":
            if re.search("verified", str(v[i])):
                t_dic["verified"] = v[i].find("label").text
            if re.search("language: english", str(v[i])):
                t_dic["en"] = v[i].find("label").text
            elif re.search("span>zh-Hant", str(v[i])):
                t_dic["cht"] = v[i].find("label").text
            elif re.search("span>zh-Hans", str(v[i])):
                t_dic["chs"] = v[i].find("label").text
            elif re.search("language: japanese", str(v[i])):
                t_dic["jp"] = v[i].find("label").text
        elif g[i].text == "Synonym":
            t_dic["synonym"] = v[i].text
        elif g[i].text == "Kana":
            t_dic["kana"] = v[i].text
    return t_dic


def get_title(id):
    url = f"http://api.anidb.net:9001/httpapi?request=anime&client=autobangumi&clientver=1&protover=1&aid={id}"
    req = requests.get(url)
    soup = BeautifulSoup(req.text, "xml")
    titles = soup.titles.find_all("title")
    all_title_info = {
        "id": id,
        "main": None,
        "en": None,
        "zh-Hans": None,
        "zh-Hant": None,
        "ja": None,
        "other": []
    }
    for title in titles:
        if title["type"] == "main":
            all_title_info["main"] = title.string
        elif title["type"] == "official":
            if title["xml:lang"] in ["en", "zh-Hant", "zh-Hans", "ja"]:
                all_title_info[title["xml:lang"]] = title.string
            else:
                break
        elif title["type"] == "synonym":
            all_title_info["other"].append(title.string)
        else:
            break
    return all_title_info


if __name__ == "__main__":
    ids = get_list(2022, 2)
    json = []
    for id in ids:
        data = get_title(id)
        print(data)
        time.sleep(2.5)
        json.append(data)
    json_config.save("season_summer.json", json)
