import os
import re
import sys
import time
import json

import qbittorrentapi
import requests
from bs4 import BeautifulSoup

import re
import json
import zhconv
import requests
import logging
import pandas as pd


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
    time_show_obj = time.strftime('%Y-%m-%d %X')
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
            print(e)

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
            sys.stdout.write(f"[{EnvInfo.time_show_obj}]  Successes adding RSS Feed." + "\n")
        except ConnectionError:
            sys.stdout.write(f"[{EnvInfo.time_show_obj}]  Error with adding RSS Feed." + "\n")
        except qbittorrentapi.exceptions.Conflict409Error:
            sys.stdout.write(f"[{EnvInfo.time_show_obj}]  RSS Already exists." + "\n")

    def run(self):
        sys.stdout.write(f"[{EnvInfo.time_show_obj}]  Start adding rules." + "\n")
        sys.stdout.flush()
        for info in self.bangumi_info:
            self.set_rule(info["title"], info["season"])
        sys.stdout.write(f"[{EnvInfo.time_show_obj}]  Finished." + "\n")
        sys.stdout.flush()


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
            sys.stdout.write(f"[{EnvInfo.time_show_obj}]   Get rules Erroe=r")
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
                print(f"[{EnvInfo.time_show_obj}]  ERROR Not match with {name}")

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
                sys.stdout.write(f"[{EnvInfo.time_show_obj}]  add {json_title} {json_season}" + "\n")
                sys.stdout.flush()
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
            print(e)
        self.recent_info = self.qbt_client.torrents_info(status_filter='completed', category="Bangumi")
        self.hash = None
        self.name = None
        self.new_name = None
        self.path_name = None
        self.count = 0
        self.rename_count = 0
        self.torrent_count = len(self.recent_info)

        logging.basicConfig(level=logging.DEBUG,
                            filename='./rename_log.txt',
                            filemode='w',
                            format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')
        self.group_character = ['字幕社', '字幕组', '字幕屋', '发布组', '动漫', '国漫', '汉化', 'raw', 'works', '工作室', '压制', '合成', '制作',
                                '搬运', '委员会', '家族', '译制', '动画', '研究所', 'sub', '翻译', '联盟', 'dream', '-rip', 'neo', 'team']
        self.group_char = ['dmhy', 'lolihouse', 'vcb', '澄空学园', 'c.c动漫', '拨雪寻春', 'mingy', 'amor', 'moozzi2',
                           '酷漫', 'skytree', 'sweetsub', 'pcsub', 'ahu-sub', 'f宅', 'captions', 'dragsterps', 'onestar',
                           '卡通', '时雨初空', 'nyaa', 'ddd', 'koten', 'reinforce', '届恋对邦小队', 'cxraw']
        with open("rule.json", encoding='utf-8') as file_obj:
            rule_json = json.load(file_obj)[0]["group_name"]
        self.group_rule = [str(x).lower() for x in rule_json]
        self.file_info = {}

    # 获取字符串出现位置
    def getStrInfo(self, char, target):
        locate = []
        for index, value in enumerate(char):
            if target == value:
                locate.append(index)
        return locate

    # 匹配某字符串最近的括号
    def get_gp(self, char, string):
        start = [x for x in self.getStrInfo(string, "[") if int(x) < int(string.find(char))][-1] + 1
        end = [x for x in self.getStrInfo(string, "]") if int(x) > int(string.find(char))][0]
        return string[start:end]

    # 清理原链接（中文字符替换为英文）
    def clean(self, file_name):
        file_name = zhconv.convert(file_name, 'zh-cn')
        # 去广告
        file_name = re.sub("[（(\[【]?(字幕)?[\u4e00-\u9fa5]{0,3}(新人|招募?新?)[\u4e00-\u9fa5]{0,5}[）)\]】]?", "", file_name)
        # 除杂
        file_name = re.sub("[（(\[【]?★?(\d{4}年[春夏秋冬]?)?[\d一二三四五六七八九十]{1,2}月新?番★?[）)\]】]?", "", file_name)
        strip = ["复制磁连", "兼容", "配音", "网盘", "\u200b", "[]"]
        for i in strip:
            file_name = file_name.replace(i, "")
        file_name = str(file_name).replace('：', ':').replace('【', '[').replace('】', ']').replace('-', '-') \
            .replace('（', '(').replace('）', ')').replace("＆", "&").replace("X", "x").replace("×", "x") \
            .replace("Ⅹ", "x").replace("-", " ").replace("_", " ")

        return file_name

    # 检索string1列表元素是否在string2列表元素中
    def find_str(self, str1, str2):
        for s1 in str1:
            for s2 in str2:
                if s1 in s2:
                    return [True, s2[1:]]
        else:
            return [False, name]

    # 检索字幕组特征
    def regognize_group(self, file_name):
        character = self.group_character
        group = self.group_char
        rule = self.group_rule
        # 字幕组（特例）特征优先级大于通用特征
        character = group + character
        # !强规则，人工录入标准名，区分大小写，优先匹配
        if "[ANi]" in file_name:
            return ["enforce", "[ani]"]
        for char in rule:
            if "[%s]" % char in file_name:
                return ["enforce", char]
        # 如果文件名以 [字幕组名] 开头
        if file_name[0] == "[":
            str_split = file_name.lower().split("]")
            # 检索特征值是否位于文件名第1、2、最后一段
            for char in character:
                if char in str_split[0] or char in str_split[1] or char in str_split[-1]:
                    return ["success", char]
            # 文件名是否为 [字幕组名&字幕组名&字幕组名] ，求求了，一集的工作量真的需要三个组一起做吗
            if self.find_str(["&", "@"], str_split)[0]:
                res = self.find_str(["&", "@"], str_split)[1]
                # 限制匹配长度，防止出bug
                if len(res) < 10:
                    return ["special", res]
            # 再匹配不上我就麻了
            return [False, file_name]
        # 文件名以 -字幕组名 结尾
        elif "-" in file_name:
            for char in character:
                if char in file_name.lower().split("-")[-1]:
                    return ["reserve", file_name.lower().split("-")[-1]]
            return [False, file_name]
        # 文件名以空格分隔 字幕组名为第一段
        else:
            for char in character:
                if char in file_name.lower().split(" ")[0]:
                    return ["blank", char]
            # 再匹配不上我就麻了
            return [False, file_name]

    # 获取字幕组名
    def get_group(self, file_name):
        # 是否匹配成功（哪种方式匹配成功）
        status = self.regognize_group(file_name)[0]
        # 检索到的特征值
        res_char = self.regognize_group(file_name)[1]
        # 强条
        if status == "enforce":
            return res_char
        # 大部分情况
        elif status == "success":
            # 如果是 [字幕组名] ，这么标准的格式直接else送走吧，剩下的匹配一下
            if "[%s]" % res_char not in file_name.lower():
                if file_name[0] == "[":
                    try:
                        # 以特征值为中心，匹配最近的中括号，八成就这个了
                        gp = self.get_gp(res_char, file_name.lower())
                        # 防止太长炸了，一般不会这么长的字幕组名
                        if len(gp) < 30:
                            print("gp:%s" % gp)
                        else:
                            print("name:%s\r\nchar:%s,gp:%s" % (file_name, res_char, gp))
                        return gp
                    except Exception as e:
                        print("bug -- res_char:%s,%s,%s" % (res_char, file_name.lower(), e))
            else:
                print("2:%s" % res_char)
                return res_char
        # 文件名以空格分隔 字幕组名为第一段
        elif status == "blank":
            if res_char in file_name.lower().split(" ")[0]:
                res = file_name.lower().split(" ")[0]
                print("blank:%s" % res)
                return res
        # 文件名为 [字幕组名&字幕组名&字幕组名]
        elif status == "special":
            print("special:%s" % res_char)
            return res_char
        # -字幕组名 在结尾
        elif status == "reserve":
            print("reserve:%s" % res_char)
            return res_char
        # 再见
        else:
            return None

    # 扒了6W数据，硬找的参数，没啥说的
    def get_dpi(self, file_name):
        dpi_list = ["4k", "2160p", "1440p", "1080p", "1036p", "816p", "810p", "720p", "576p", "544P", "540p", "480p",
                    "1080i", "1080+",
                    "3840x2160", "1920x1080", "1920x1036", "1920x804", "1920x800", "1536x864", "1452x1080", "1440x1080",
                    "1280x720", "1272x720", "1255x940", "1024x768", "1024X576", "960x720", "948x720", "896x672",
                    "872x480",
                    "848X480", "832x624", "704x528", "640x480",
                    "mp4_1080", "mp4_720"]
        for i in dpi_list:
            dpi = str(file_name).lower().find(i)
            if dpi > 0:
                return str(i)
        return None

    # 获取语种
    def get_language(self, file_name):
        lang = []
        # 中文标示
        try:
            lang.append(re.search("[（(\[【]?((日?[粤中简繁英]日?(文|体|双?语)?/?){1,5}(双?字幕)?)[）)\]】]?", str(file_name)).group(1))
        except Exception as e:
            print(e)
        # 英文标示
        try:
            lang.append(
                re.search("[（(\[【]?(((CHT|CHS|GB|JP|CN|BIG5)[/ _]?){1,3})[）)\]】]?", str(file_name)).group(1).lower())
        except Exception as e:
            logging.info(e)
        if lang:
            return lang
        else:
            return None

    # 文件种类
    def get_type(self, file_name):
        type_list = []
        # 英文标示
        try:
            type_list.append(re.search("[（(\[【]?(((flac(x\d)?|mp4|mkv|mp3)[ -]?){1,3})[）)\]】]?",
                                       str(file_name).lower()).group(1).lower())
        except Exception as e:
            logging.info(e)
        if type_list:
            return type_list
        else:
            return None

    # 编码格式
    def get_code(self, file_name):
        code = []
        # 英文标示
        try:
            code.append(re.search("[（(\[【]?(((x26[45]|hevc|aac|avc|((10|8)[ -]?bit))[ -]?(x\d)?[ -]?){1,5})[）)\]】]?",
                                  str(file_name).lower()).group(1).lower())
        except Exception as e:
            logging.info(e)
        if code:
            return code
        else:
            return None

    # 来源
    def get_source(self, file_name):
        file_name = str(file_name).lower()
        type_list = []
        # 英文标示
        for i in range(3):
            try:
                res = re.search(
                    "[（(\[【]?((bd|remux|tv|bilibili|b ?global|baha|web[ -]?(dl|rip))[ -]?(iso|mut|rip)?)[）)\]】]?",
                    file_name).group(1).lower()
                if res not in type_list:
                    type_list.append(res)
            except Exception as e:
                logging.info(e)
            for res in type_list:
                file_name = file_name.replace(res, "")
        if type_list:
            return type_list
        else:
            return None

    # 获取季度
    def get_season(self, file_name):
        try:
            season = re.search("(((final ?season|第) ?(\d{1,2}|[一二三]|最终)(部|季|季度|丁目))|(season ?\d)|(s\d{1,2}))",
                               str(file_name).lower()).group(1)
            return season.lower()
        except Exception as e:
            logging.info(e)

    # 获取集数
    def get_episode(self, file_name):
        try:  # [10 11]集点名批评这种命名方法，几个国漫的组
            episode = re.search("[\[(](\d{1,3} \d{1,3})( fin| Fin|\(全集\))?[)\]]", str(file_name)).group(1)
            return episode.lower()
        except Exception as e:
            try:  # 这里匹配ova 剧场版 不带集数的合集 之类的
                episode = re.search("[\[ 第](_\d{1,3}集|ova|剧场版|全集|OVA ?\d{0,2}|合集|\d{0,3}\.\d)[集话章\]\[]",
                                    str(file_name)).group(1)
                return episode.lower()
            except Exception as e:
                try:  # 标准单集 sp单集
                    episode = re.search("[\[ 第|e]((sp)?\d{1,4}v?2?3?)(集|话|章| |]|\[)", str(file_name).lower()).group(1)
                    return episode.lower()
                except Exception as e:
                    try:  # xx-xx集
                        episode = re.search("[\[ 第(](\d{1,3}[ -]\d{1,3})(话| |]|\(全集\)|全集|fin)",
                                            str(file_name).lower()).group(
                            1)
                        return episode.lower()
                    except Exception as e:
                        logging.info(e)
                        return None

    # 获取版本
    def get_vision(self, file_name):
        try:
            vision = re.search("[（(\[【]?([\u4e00-\u9fa5]{0,2}|v\d)((版本?|修复?正?)|片源?)[）)\]】]?",
                               str(file_name).lower()).group(
                1)
            return vision.lower()
        except Exception as e:
            logging.info(e)
            return None

    # 获取字幕类型
    def get_ass(self, file_name):
        type_list = ["附外挂字幕", "外挂字幕", "内嵌字幕", "内封字幕", "外挂", "内嵌", "内封", "+ass", "ass"]
        for i in type_list:
            file_type = str(file_name).lower().find(i)
            if file_type > 0:
                return str(i)
        return None

    # 拿到的数据挨个测试
    def get_info(self, file_name):
        name = self.clean(file_name)
        # 获取到的信息
        info = {
            "group": self.get_group(name),
            "dpi": self.get_dpi(name),
            "season": self.get_season(name),
            "episode": self.get_episode(name),
            "vision": self.get_vision(name),
            "lang": self.get_language(name),
            "ass": self.get_ass(name),
            "type": self.get_type(name),
            "code": self.get_code(name),
            "source": self.get_source(name)
        }
        # 字母全部小写
        clean_name = name.lower()
        # 去除拿到的有效信息
        for k, v in info.items():
            if v is not None:
                if type(v) is list:
                    for i in v:
                        clean_name = clean_name.replace(i, "")
                else:
                    clean_name = clean_name.replace(v, "")
        # 除杂
        clean_list = ["pc&psp", "pc&psv", "fin", "opus", "srt", "tvb", "bangumi.online", "donghua",
                      "话全", "第话", "第集", " 话", " 集", "+", "@", "。"]
        for i in clean_list:
            clean_name = clean_name.replace(i, "").replace(" ]", "]").replace("[ ", "[").replace("  ", "")
        # 分隔各字段
        clean_name = clean_name.replace("[", "").replace("]", " ").replace("()", "").replace("( )", "")
        # 去除多余空格
        clean_name = clean_name.replace("\n\n", "\n").replace("\n\n", "\n").replace("\n\n", "\n").replace("\n\n", "\n")
        # 剩下来的几乎就是干净番名了，再刮不到不管了
        info["clean_name"] = clean_name
        return info

    def rename_normal(self, idx):
        self.name = self.recent_info[idx].name
        self.hash = self.recent_info[idx].hash
        self.path_name = self.recent_info[idx].content_path.split("/")[-1]

        normal_name = self.file_info["clean_name"]
        if self.file_info["group"] is not None:
            normal_name = "[%s]" % self.file_info["group"] + normal_name
        if self.file_info["season"] is not None:
            normal_name = normal_name + " " + self.file_info["season"]
        else:
            normal_name = normal_name + " S01"
        if self.file_info["episode"] is not None:
            normal_name = normal_name + " E" + self.file_info["episode"]
        self.new_name = normal_name

    def rename_pn(self, idx):
        self.name = self.recent_info[idx].name
        self.hash = self.recent_info[idx].hash
        self.path_name = self.recent_info[idx].content_path.split("/")[-1]
        normal_name = self.file_info["clean_name"]
        if self.file_info["group"] is not None:
            normal_name = "[%s]" % self.file_info["group"] + normal_name
        if self.file_info["season"] is not None:
            normal_name = normal_name + " " + self.file_info["season"]
        else:
            normal_name = normal_name + " S01"
        if self.file_info["episode"] is not None:
            normal_name = normal_name + " E" + self.file_info["episode"]
        self.new_name = normal_name

    def rename(self):
        if self.path_name != self.new_name:
            self.qbt_client.torrents_rename_file(torrent_hash=self.hash, old_path=self.path_name,
                                                 new_path=self.new_name)
            sys.stdout.write(f"[{time.strftime('%Y-%m-%d %X')}]  {self.path_name} >> {self.new_name}")
            self.count += 1
        else:
            return

    def clear_info(self):
        self.file_info = {}

    def print_result(self):
        sys.stdout.write(f"[{EnvInfo.time_show_obj}]  已完成对{self.torrent_count}个文件的检查" + '\n')
        sys.stdout.write(f"[{EnvInfo.time_show_obj}]  已对其中{self.count}个文件进行重命名" + '\n')
        sys.stdout.write(f"[{EnvInfo.time_show_obj}]  完成" + '\n')
        sys.stdout.flush()

    def run(self):
        if EnvInfo.method not in ['pn', 'normal']:
            print('error method')
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
