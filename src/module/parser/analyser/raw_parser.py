import logging
import re
from dataclasses import dataclass

from module.models import Episode

logger = logging.getLogger(__name__)

EPISODE_RE = re.compile(r"\d+")
EPISODE_COLLECTION_RE = re.compile(r"\d+-\d+|\d+ - \d+")
TITLE_RE = re.compile(
    r"(.*|\[.*])( -? \d+| \d+ |\[\d+]|\[\d+.?[vV]\d{1}]|[第]?\d+[话話集]|\[\d+.?END])(.*)"
)
TITLE_COLLECTION_RE = re.compile(
    r"(.*|\[.*])(\[\d+-\d+]| \d+-\d+ |[第]\d+-\d+[话話集]|\[\d+-\d+[全]|\[\d+-\d+[话話合集F+P])(.*)"
)
RESOLUTION_RE = re.compile(r"1080|720|2160|4K")
SOURCE_RE = re.compile(r"B-Global|[Bb]aha|[Bb]ilibili|AT-X|Web")
SUB_RE = re.compile(r"[简繁日字幕]|CH|BIG5|GB")

PREFIX_RE = re.compile(r"[^\w\s\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff-]")

CHINESE_NUMBER_MAP = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


class RawParser:
    @staticmethod
    def get_group(name: str) -> str:
        return re.split(r"[\[\]]", name)[1]

    @staticmethod
    def pre_process(raw_name: str) -> str:
        return raw_name.replace("【", "[").replace("】", "]")

    @staticmethod
    def prefix_process(raw: str, group: str) -> str:
        raw = re.sub(f".{group}.", "", raw)
        raw_process = PREFIX_RE.sub("/", raw)
        arg_group = raw_process.split("/")
        for arg in arg_group:
            if re.search(r"新番|月?番", arg) and len(arg) <= 5:
                raw = re.sub(f".{arg}.", "", raw)
            elif re.search(r"港澳台地区", arg):
                raw = re.sub(f".{arg}.", "", raw)
        return raw

    @staticmethod
    def season_process(season_info: str):
        name_season = season_info
        # if re.search(r"新番|月?番", season_info):
        #     name_season = re.sub(".*新番.", "", season_info)
        #     # 去除「新番」信息
        # name_season = re.sub(r"^[^]】]*[]】]", "", name_season).strip()
        season_rule = r"S\d{1,2}|Season \d{1,2}|[第].[季期]"
        name_season = re.sub(r"[\[\]]", " ", name_season)
        seasons = re.findall(season_rule, name_season)
        if not seasons:
            return name_season, "", 1
        name = re.sub(season_rule, "", name_season)
        for season in seasons:
            season_raw = season
            if re.search(r"Season|S", season) is not None:
                season = int(re.sub(r"Season|S", "", season))
                break
            elif re.search(r"[第 ].*[季期(部分)]|部分", season) is not None:
                season_pro = re.sub(r"[第季期 ]", "", season)
                try:
                    season = int(season_pro)
                except ValueError:
                    season = CHINESE_NUMBER_MAP[season_pro]
                    break
        return name, season_raw, season

    @staticmethod
    def name_process(name: str):
        name_en, name_zh, name_jp = None, None, None
        name = name.strip()
        name = re.sub(r"[(（]仅限港澳台地区[）)]", "", name)
        split = re.split("/|\s{2}|-\s{2}", name)
        while "" in split:
            split.remove("")
        if len(split) == 1:
            if re.search("_{1}", name) is not None:
                split = re.split("_", name)
            elif re.search(" - {1}", name) is not None:
                split = re.split("-", name)
        if len(split) == 1:
            split_space = split[0].split(" ")
            for idx, item in enumerate(split_space):
                if re.search(r"^[\u4e00-\u9fa5]{2,}", item) is not None:
                    split_space.remove(item)
                    split = [item.strip(), " ".join(split_space).strip()]
                    break
        for item in split:
            if re.search(r"[\u0800-\u4e00]{2,}", item) and not name_jp:
                name_jp = item.strip()
            elif re.search(r"[\u4e00-\u9fa5]{2,}", item) and not name_zh:
                name_zh = item.strip()
            elif re.search(r"[a-zA-Z]{3,}", item) and not name_en:
                name_en = item.strip()
        return name_en, name_zh, name_jp

    @staticmethod
    def find_tags(other):
        elements = re.sub(r"[\[\]()（）]", " ", other).split(" ")
        # find CHT
        sub, resolution, source = None, None, None
        for element in filter(lambda x: x != "", elements):
            if SUB_RE.search(element):
                sub = element
            elif RESOLUTION_RE.search(element):
                resolution = element
            elif SOURCE_RE.search(element):
                source = element
        return RawParser.clean_sub(sub), resolution, source

    @staticmethod
    def clean_sub(sub: str | None) -> str | None:
        if sub is None:
            return sub
        return re.sub(r"_MP4|_MKV", "", sub)

    def process(self, raw_title: str):
        raw_title = raw_title.strip()
        content_title = self.pre_process(raw_title)
        # 预处理标题
        group = self.get_group(content_title)
        # 翻译组的名字
        match_obj = TITLE_RE.match(content_title)
        is_collection = 0

        if not match_obj:
            # See if it's a collection
            match_obj = TITLE_COLLECTION_RE.match(content_title)
            # It doesn't matter if match_obj empty, for now (o ‵-′)ノ
            is_collection = 1
        season_info, episode_info, other = list(map(
            lambda x: x.strip(), match_obj.groups()
        ))
        process_raw = self.prefix_process(season_info, group)
        # 处理 前缀
        raw_name, season_raw, season = self.season_process(process_raw)
        # 处理 第n季
        name_en, name_zh, name_jp = "", "", ""
        try:
            name_en, name_zh, name_jp = self.name_process(raw_name)
            # 处理 名字
        except ValueError:
            pass
        # 处理 集数
        # Use string format compatible collection mode
        episode = "0"
        if not is_collection:
            raw_episode = EPISODE_RE.search(episode_info)
        else:
            raw_episode = EPISODE_COLLECTION_RE.search(episode_info)
        if raw_episode:
            episode = raw_episode.group()
        sub, dpi, source = self.find_tags(other)  # 剩余信息处理
        return name_en, name_zh, name_jp, season, season_raw, episode, sub, dpi, source, group

    def analyse(self, raw: str) -> Episode | None:
        ret = self.process(raw)
        if ret is None:
            logger.error(f"Parser cannot analyse {raw}")
            return None
        name_en, name_zh, name_jp, season, sr, episode, \
            sub, dpi, source, group = ret
        return Episode(name_en, name_zh, name_jp, season, sr, episode, sub, group, dpi, source)


if __name__ == '__main__':
    test_list = [
        "[Lilith-Raws] 关于我在无意间被隔壁的天使变成废柴这件事 / Otonari no Tenshi-sama - 09 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4]",
        "【幻樱字幕组】【4月新番】【古见同学有交流障碍症 第二季 Komi-san wa, Komyushou Desu. S02】【22】【GB_MP4】【1920X1080】",
        "[百冬练习组&LoliHouse] BanG Dream! 少女乐团派对！☆PICO FEVER！ / Garupa Pico: Fever! - 26 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕][END]",
        "[桜都字幕组][寒蝉鸣泣之时 业/Higurashi no Naku Koro ni Gou][18-22][1080P][简体内嵌]",
        "[桜都字幕组][寒蝉鸣泣之时 业/Higurashi no Naku Koro ni Gou][24][1080P][繁体内嵌]",
        "【DHR百合组】[NEW GAME!!][11][繁体][720P][MP4]",
        "[澄空学园] NEW GAME!! 第12话 MP4 720p 完",
        "[澄空学园] NEW GAME!! 第11话 MP4 720p",
        "【极影字幕社】 ★ 魔女之旅 01-12 BIG5 1080P MP4 BDrip HEVC",
        "【极影字幕社】 ★10月新番 魔女之旅 12 GB 1080P MP4",
        "[爱恋&漫猫字幕组][1月新番][寒蝉鸣泣之时业][Higurashi no Naku Koro ni Gou][01-24Fin][WEB][1080p][AVC][简中]",
        "[千夏字幕组&LoliHouse] 科学超电磁炮T / Toaru Kagaku no Railgun T [01-25合集][WebRip 1080p HEVC-10bit AAC][简繁内封字幕][Fin]",
        "[桜都字幕组][某科学的超电磁砲T/To Aru Kagaku no Railgun T][1-25][END][CHT][1080P]",
        "【铃风字幕组】【科学超电磁砲T/To_Aru_Kagaku_no_Railgun_T】[01-25+PV][1080P][MKV][繁体外挂][招募翻译]",
        "【极影字幕社】★ 某科学的超电磁炮T （科学超电磁炮T） 第01-25集 GB_CN 720p HEVC MP4",
        "【澄空学园&动漫国字幕组】★01月新番[科学的超电磁炮T][01-25][合集][720P][繁体][MP4]",
        "[Lilith-Raws] 科学超电磁砲T / Toaru Kagaku no Railgun S03 - 25 [BiliBili][WEB-DL][1080p][AVC AAC][CHT][MKV]",
        "[星空字幕组][末日时在做什么？有没有空？可以来拯救吗？][01-12][繁日双语][1080P][BDrip][MP4] [复制磁连]",
        "【DHRx幻之】[末日时在做甚麽？有没有空？可以来拯救吗？_Shuumatsu Nani Shitemasu ka? Isogashii desu ka? Sukutte Moratte Ii desu ka?][07-08][繁体BIG5][720P]",
        "[澄空学园] NEW GAME!! 第01-12话 MKV 1080p HEVC 简体外挂 合集",
        "【西农YUI汉化组】★七月新番【New Game!!】 第01-12话 BIG5繁体 720P MP4",
        "【DMHY】【NEW GAME!!】[01-12][合集][720P][繁体]",
        "[银光字幕组][七月新番★][NEW GAME!!][01-12全][BIG5][HDrip][X264-AAC][720P][MP4]",
        "【DHR百合组】[NEW GAME!!][01-12全][繁体][720P][MP4](合集版本)"
    ]
    parser = RawParser()
    for l in test_list:
        ep = parser.analyse(l)
        print(f"en: {ep.title_en}, zh: {ep.title_zh}, jp: {ep.title_jp}, group: {ep.group}")

