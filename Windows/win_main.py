import os
import re
import sys
import time
import json
import logging

import qbittorrentapi
import requests
from bs4 import BeautifulSoup

import requests.packages.urllib3.util.ssl_

requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS = 'ALL'

logger = logging.getLogger(__name__)

class EnvInfo:
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    elif __file__:
        application_path = os.path.dirname(__file__)
    path = os.path.join(application_path, 'config.json')
    with open(path) as f:
        data = f.read()
        info = json.loads(data)
    host_ip = info["host_ip"]
    sleep_time = float(info["time"])
    user_name = info["user_name"]
    password = info["password"]
    rss_link = info["rss_link"]
    download_path = info["download_path"]
    method = info["method"]
    # rss_link = "https://mikanani.me/RSS/MyBangumi?token=Td8ceWZZv3s2OZm5ji9RoMer8vk5VS3xzC1Hmg8A26E%3d"
    rule_url = "https://raw.githubusercontent.com/EstrellaXD/Bangumi_Auto_Collector/main/AutoBangumi/config/rule.json"
    bangumi_info = info["bangumi_info"]


class SetRule:
    def __init__(self):
        self.bangumi_info = EnvInfo.bangumi_info
        self.rss_link = EnvInfo.rss_link
        self.host_ip = EnvInfo.host_ip
        self.user_name = EnvInfo.user_name
        self.password = EnvInfo.password
        self.download_path = EnvInfo.download_path
        self.qb = qbittorrentapi.Client(host=self.host_ip, username=self.user_name, password=self.password)
        try:
            self.qb.auth_log_in()
        except qbittorrentapi.LoginFailed as e:
            logger.exception(e)

    def set_rule(self, bangumi_name, season):
        rule = {
            'enable': True,
            'mustContain': bangumi_name,
            'mustNotContain': '720',
            'useRegx': True,
            'episodeFilter': '',
            'smartFilter': False,
            'previouslyMatchedEpisodes': [],
            'affectedFeeds': [self.rss_link],
            'ignoreDays': 0,
            'lastMatch': '',
            'addPaused': False,
            'assignedCategory': 'Bangumi',
            'savePath': str(os.path.join(self.download_path, bangumi_name, season))
        }
        self.qb.rss_set_rule(rule_name=bangumi_name, rule_def=rule)

    def rss_feed(self):
        try:
            self.qb.rss_remove_item(item_path="Mikan_RSS")
            self.qb.rss_add_feed(url=self.rss_link, item_path="Mikan_RSS")
            logger.debug("Successes adding RSS Feed." + "\n")
        except ConnectionError:
            logger.debug("Error with adding RSS Feed." + "\n")
        except qbittorrentapi.exceptions.Conflict409Error:
            logger.debug("RSS Already exists." + "\n")

    def run(self):
        logger.debug("Start adding rules." + "\n")
        for info in self.bangumi_info:
            self.set_rule(info["title"], info["season"])
        logger.debug("Finished." + "\n")


class MatchRule:
    split_rule = r"\[|\]|\【|\】|\★|\（|\）|\(|\)"
    last_rule = r"(.*)( \-)"
    sub_title = r"[^\x00-\xff]{1,}| \d{1,2}^.*|\·"
    match_rule = r"(S\d{1,2}(.*))"
    season_match = r"(.*)(Season \d{1,2}|S\d{1,2}|第.*季|第.*期)"


class CollectRSS:
    def __init__(self):
        self.bangumi_list = []
        try:
            self.rules = requests.get(EnvInfo.rule_url).json()
        except ConnectionError:
            logger.debug(" Get rules Erroe=r")
        rss = requests.get(EnvInfo.rss_link, 'utf-8')
        soup = BeautifulSoup(rss.text, 'xml')
        self.items = soup.find_all('item')
        self.info = EnvInfo.bangumi_info

    def get_info_list(self):
        for item in self.items:
            name = item.title.string
            # debug 用
            # print(name)
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
                            self.bangumi_list.append(bangumi_title)
                        # debug
                        # print(bangumi_title)
                        break
                if exit_flag:
                    break
            if not exit_flag:
                logger.debug("ERROR Not match with {name}")

    def put_info_json(self):
        had_data = []
        for data in self.info:
            had_data.append(data["title"])
        for title in self.bangumi_list:
            match_title_season = re.match(MatchRule.season_match, title, re.I)
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
                logger.debug("add {json_title} {json_season}" + "\n")
        EnvInfo.info["bangumi_info"] = self.info
        with open(EnvInfo.path, 'w', encoding='utf8') as f:
            data = json.dumps(EnvInfo.info, indent=4, separators=(',', ': '), ensure_ascii=False)
            f.write(data)

    def run(self):
        self.get_info_list()
        self.put_info_json()


class qBittorrentRename:

    def __init__(self):
        self.qbt_client = qbittorrentapi.Client(host=EnvInfo.host_ip,
                                                username=EnvInfo.user_name,
                                                password=EnvInfo.password)
        try:
            self.qbt_client.auth_log_in()
        except qbittorrentapi.LoginFailed as e:
            logger.debug(e)
        self.recent_info = self.qbt_client.torrents_info(status_filter='completed', category="Bangumi")
        self.hash = None
        self.name = None
        self.new_name = None
        self.path_name = None
        self.count = 0
        self.rename_count = 0
        self.torrent_count = len(self.recent_info)
        self.rules = [r'(.*)\[(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)',
                      r'(.*)\[E(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)',
                      r'(.*)\[第(\d*\.*\d*)话(?:END)?\](.*)',
                      r'(.*)\[第(\d*\.*\d*)話(?:END)?\](.*)',
                      r'(.*)第(\d*\.*\d*)话(?:END)?(.*)',
                      r'(.*)第(\d*\.*\d*)話(?:END)?(.*)',
                      r'(.*)- (\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)? (.*)']

    def rename_normal(self, idx):
        self.name = self.recent_info[idx].name
        self.hash = self.recent_info[idx].hash
        self.path_name = self.recent_info[idx].content_path.split("/")[-1]
        file_name = self.name
        for rule in self.rules:
            matchObj = re.match(rule, file_name, re.I)
            if matchObj is not None:
                self.new_name = f'{matchObj.group(1).strip()} E{matchObj.group(2)}{matchObj.group(3)}'

    def rename_pn(self, idx):
        self.name = self.recent_info[idx].name
        self.hash = self.recent_info[idx].hash
        self.path_name = self.recent_info[idx].content_path.split("/")[-1]
        n = re.split(r'\[|\]', self.name)
        file_name = self.name.replace(f'[{n[1]}]', '')
        for rule in self.rules:
            matchObj = re.match(rule, file_name, re.I)
            if matchObj is not None:
                self.new_name = re.sub(r'\[|\]', '', f'{matchObj.group(1).strip()} E{matchObj.group(2)}{n[-1]}')

    def rename(self):
        if self.path_name != self.new_name:
            self.qbt_client.torrents_rename_file(torrent_hash=self.hash, old_path=self.path_name,
                                                 new_path=self.new_name)
            logger.debug(f"{self.path_name} >> {self.new_name}")
            self.count += 1
        else:
            return

    def clear_info(self):
        self.name = None
        self.hash = None
        self.new_name = None
        self.path_name = None

    def print_result(self):
        logger.debug("已完成对{self.torrent_count}个文件的检查")
        logger.debug("已对其中{self.count}个文件进行重命名")
        logger.debug("完成")

    def run(self):
        if EnvInfo.method not in ['pn', 'normal']:
            logger.error('error method')
        elif EnvInfo.method == 'normal':
            for i in range(0, self.torrent_count + 1):
                try:
                    self.rename_normal(i)
                    self.rename()
                    self.clear_info()
                except:
                    self.print_result()
        elif EnvInfo.method == 'pn':
            for i in range(0, self.torrent_count + 1):
                try:
                    self.rename_pn(i)
                    self.rename()
                    self.clear_info()
                except:
                    self.print_result()


if __name__ == "__main__":
    while True:
        CollectRSS().run()
        SetRule().run()
        qBittorrentRename().run()
        time.sleep(EnvInfo.sleep_time)
