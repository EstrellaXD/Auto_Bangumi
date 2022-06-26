import logging
import re
from parser.episode import Episode

logger = logging.getLogger(__name__)

# TODO: 正则表达式可以放到全局，改成 re.compile 的形式

class RawParser:

    def __init__(self) -> None:
        pass

    def get_group(self, name: str) -> str:
        return re.split(r"[\[\]]", name)[1]

    @staticmethod
    def pre_process(raw_name: str) -> str:
        return raw_name.replace("【", "[").replace("】", "]")

    @staticmethod
    def second_process(raw_name):
        if re.search(r"新番|月?番", raw_name):
            pro_name = re.sub(".*新番.", "", raw_name)
        else:
            pro_name = re.sub(r"^[^]】]*[]】]", "", raw_name).strip()
        return pro_name

    @staticmethod
    def season_process(name_season):
        season_rule = r"S\d{1,2}|Season \d{1,2}|[第].[季期]"
        season_map = {
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
                    season = season_map[season_pro]
                    break
        return name, season_raw, season

    @staticmethod
    def name_process(name):
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

    @staticmethod
    def find_tags(other):
        elements = re.sub(r"[\[\]()（）]", " ", other).split(" ")
        while "" in elements:
            elements.remove("")
        # find CHT
        sub = None
        dpi = None
        source = None
        for element in elements:
            if re.search(r"[简繁日字幕]|CH|BIG5|GB", element) is not None:
                # TODO: 这里需要改成更精准的匹配，可能不止 _MP4 ?
                sub = element.replace("_MP4", "")
            elif re.search(r"1080|720|2160|4K", element) is not None:
                dpi = element
            elif re.search(r"B-Global|[Bb]aha|[Bb]ilibili|AT-X|Web", element) is not None:
                source = element
        return sub, dpi, source

    def process(self, raw_name):
        raw_name = self.pre_process(raw_name)
        group = self.get_group(raw_name)

        match_obj = re.match(
            r"(.*|\[.*])( -? \d{1,3} |\[\d{1,3}]|\[\d{1,3}.?[vV]\d{1}]|[第]\d{1,3}[话話集]|\[\d{1,3}.?END])(.*)",
            raw_name,
        )
        name_season = self.second_process(match_obj.group(1))
        name, season_raw, season = self.season_process(name_season)
        name, name_group = self.name_process(name)
        episode = int(re.findall(r"\d{1,3}", match_obj.group(2))[0])
        other = match_obj.group(3).strip()
        sub, dpi, source = self.find_tags(other)
        return name, season, season_raw, episode, sub, dpi, source, name_group, group

    def analyse(self, raw) -> Episode:
        try:
            name, season, sr, episode, \
                sub, dpi, source, ng, group = self.process(raw)
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
