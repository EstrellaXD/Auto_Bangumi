import logging
import re
from bangumi_parser.episode import Episode

logger = logging.getLogger(__name__)


class ParserLV2:
    def __init__(self) -> None:
        self.name = None

    def pre_process(self, raw_name):
        if re.search(r"新番|月?番", raw_name):
            pro_name = re.sub(".*新番.", "", raw_name)
        else:
            pro_name = re.sub(r"^[^]】]*[]】]", "", raw_name).strip()
        return pro_name

    def season_process(self, name_season):
        season_rule = r"S\d{1,2}|Season \d{1,2}|[第].[季期]"
        season_map = {
            "一": 1,
            "二": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "十": 10,
        }
        name_season = re.sub(r"[\[\]]", " ", name_season)
        seasons = re.findall(season_rule, name_season)
        if not seasons:
            name = name_season
            season = 1
        else:
            name = re.sub(season_rule, "", name_season)
            for season in seasons:
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
        return name, season

    def name_process(self, name):
        split = re.split("/|  |-  ", name.replace("（仅限港澳台地区）", ""))
        while "" in split:
            split.remove("")
        if len(split) == 1:
            if re.search("_{1}", split[0]) is not None:
                split = re.split("_", split[0])
        if len(split) == 1:
            if re.search(" - {1}", split[0]) is not None:
                split = re.split("-", split[0])
        if len(split) == 1:
            match_obj = re.match(r"([^\x00-\xff]{1,}) ([\x00-\xff]{4,})", split[0])
            if match_obj is not None:
                return match_obj.group(2)
        for name in split:
            if re.search("[\x00-\xff]{4}", name.strip()) is not None:
                return name
        return split[0]

    def process(self, raw_name):
        raw_name = raw_name.replace("【", "[").replace("】", "]")
        match_obj = re.match(r"(.*|\[.*])( -? \d{1,3} |\[\d{1,3}]|\[\d{1,3}.?[vV]\d{1}]|[第第]\d{1,3}[话話集集]|\[\d{1,3}.?END])(.*)", raw_name)
        name_season = self.pre_process(match_obj.group(1))
        name, season = self.season_process(name_season)
        name = self.name_process(name).strip()
        episode = int(re.findall(r"\d{1,3}", match_obj.group(2))[0])
        other = match_obj.group(3).strip()
        language = None
        return name, season, episode

    def run(self, raw) -> Episode:
        try:
            name, season, episode = self.process(raw)
            info = Episode()
            info.title = name
            info.season_info.number = season
            info.EpisodeInfo.number = episode
        except:
            logger.warning(f"ERROR match {raw}")


if __name__ == "__main__":
    import sys, os

    sys.path.append(os.path.dirname(".."))
    from const import BCOLORS

    parser = ParserLV2()
    with (open("bangumi_parser/names.txt", "r", encoding="utf-8") as f):
        err_count = 0
        for name in f:
            if name != "":
                try:
                    print(name)
                    title, season, episode = parser.process(name)
                    print(title)
                    print(season)
                    print(episode)
                except:
                    if re.search(r"\d{1,3}[-~]\d{1,3}|OVA|BD|電影|剧场版|老番|冷番|OAD|合集|劇場版|柯南|海賊王|蜡笔小新|整理|樱桃小丸子", name) is None:
                        print(f"{BCOLORS._(BCOLORS.HEADER, name)}")
                        err_count += 1
        print(BCOLORS._(BCOLORS.WARNING, err_count))

