import logging
import re
from dataclasses import dataclass

from module.models import Episode

logger = logging.getLogger(__name__)

EPISODE_RE = re.compile(r"\d+")
TITLE_RE = re.compile(
    r"(.*|\[.*])( -? \d+|\[\d+]|\[\d+.?[vV]\d{1}]|[第]?\d+[话話集]|\[\d+.?END])(.*)"
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
        # 处理标题
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
        raw_episode = EPISODE_RE.search(episode_info)
        episode = 0
        if raw_episode is not None:
            episode = int(raw_episode.group())
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
        "[百冬练习组&LoliHouse] BanG Dream! 少女乐团派对！☆PICO FEVER！ / Garupa Pico: Fever! - 26 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕][END]"
    ]
    parser = RawParser()
    for l in test_list:
        ep = parser.analyse(l)
        print(f"en: {ep.title_en}, zh: {ep.title_zh}, jp: {ep.title_jp}, group: {ep.group}")

