import logging
import re
from parser.episode import Episode

logger = logging.getLogger(__name__)

EPISODE_RE = re.compile(r"\d+")
TITLE_RE = re.compile(
    r"(.*|\[.*])( -? \d+ |\[\d+]|\[\d+.?[vV]\d{1}]|[第]\d+[话話集]|\[\d+.?END])(.*)"
)
RESOLUTION_RE = re.compile(r"1080|720|2160|4K")
SOURCE_RE = re.compile(r"B-Global|[Bb]aha|[Bb]ilibili|AT-X|Web")
SUB_RE = re.compile(r"[简繁日字幕]|CH|BIG5|GB")

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
    def season_process(season_info: str):
        if re.search(r"新番|月?番", season_info):
            name_season = re.sub(".*新番.", "", season_info)
        else:
            name_season = re.sub(r"^[^]】]*[]】]", "", season_info).strip()

        season_rule = r"S\d{1,2}|Season \d{1,2}|[第].[季期]"
        name_season = re.sub(r"[\[\]]", " ", name_season)
        seasons = re.findall(season_rule, name_season)
        if not seasons:
            return name_season, "", 1
        name = re.sub(season_rule, "", name_season)
        for season in seasons:
            season_raw = season
            if re.search(r"S|Season", season) is not None:
                season = int(re.sub(r"S|Season", "", season))
                break
            elif re.search(r"[第 ].*[季期]", season) is not None:
                season_pro = re.sub(r"[第季期 ]", "", season)
                try:
                    season = int(season_pro)
                except ValueError:
                    season = CHINESE_NUMBER_MAP[season_pro]
                    break
        return name, season_raw, season

    @staticmethod
    def name_process(name: str):
        name = name.strip()
        split = re.split("/|  |-  ", name.replace("（仅限港澳台地区）", ""))
        while "" in split:
            split.remove("")
        if len(split) == 1:
            if re.search("_{1}", name) is not None:
                split = re.split("_", name)
            elif re.search(" - {1}", name) is not None:
                split = re.split("-", name)
        if len(split) == 1:
            match_obj = re.match(
                r"([^\x00-\xff]{1,})(\s)([\x00-\xff]{4,})", name)
            if match_obj is not None:
                return match_obj.group(3), split
        compare = 0
        for name in split:
            l = re.findall("[aA-zZ]{1}", name).__len__()
            if l > compare:
                compare = l
        for name in split:
            if re.findall("[aA-zZ]{1}", name).__len__() == compare:
                return name.strip(), split
        raise ValueError()

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
        # TODO: 这里需要改成更精准的匹配，可能不止 _MP4 ?
        return sub.replace("_MP4", "")

    def process(self, raw_title: str):
        raw_title = raw_title.strip()

        content_title = self.pre_process(raw_title)  # 预处理标题
        group = self.get_group(content_title)  # 翻译组的名字

        match_obj = TITLE_RE.match(content_title)  # 处理标题

        season_info, episode_info, other = list(map(
            lambda x: x.strip(), match_obj.groups()
        ))

        raw_name, season_raw, season = self.season_process(season_info)  # 处理 第n季
        name, name_group = "", ""
        try:
            name, name_group = self.name_process(raw_name)  # 处理 名字
        except ValueError:
            pass

        # 处理 集数
        raw_episode = EPISODE_RE.search(episode_info)
        episode = 0
        if raw_episode is not None:
            episode = int(raw_episode.group())

        sub, dpi, source = self.find_tags(other)  # 剩余信息处理

        return name, season, season_raw, episode, sub, dpi, source, name_group, group

    def analyse(self, raw):
        try:
            ret = self.process(raw)
            if ret is None:
                return None
            name, season, sr, episode, \
                sub, dpi, source, ng, group = ret
        except Exception as e:
            logger.error(f"ERROR match {raw} {e}")
            return None
        info = Episode()
        info.title = name
        info.season_info.number = season
        info.season_info.raw = sr
        info.ep_info.number = episode
        info.subtitle = sub
        info.dpi = dpi
        info.source = source
        info.title_info.group = ng
        info.group = group
        return info


if __name__ == "__main__":
    test = RawParser()
    ep = test.analyse("[Nekomoe kissaten][Summer Time Rendering - 11 [1080p][JPTC].mp4")
    print(ep.title, ep.dpi)
