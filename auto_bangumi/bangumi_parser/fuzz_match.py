from thefuzz import fuzz
import logging
from utils import json_config

logger = logging.getLogger(__name__)


class FuzzMatch:
    def __init__(self):
        self.match_data = json_config.load("/Users/Estrella/Developer/Bangumi_Auto_Collector/resource/season_data.json")

    def match(self, title, info: dict):
        compare_value = []
        for type in ["main", "en", "ja", "zh-Hans", "zh-Hant"]:
            if info[type] is not None:
                a = fuzz.token_sort_ratio(title.lower(), info[type].lower())
                compare_value.append(a)
        for compare in info["other"]:
            a = fuzz.token_sort_ratio(title.lower(), compare.lower())
            compare_value.append(a)
        return max(compare_value)

    def find_max_name(self, title):
        max_value = 0
        max_info = None
        for info in self.match_data:
            a = self.match(title, info)
            if a > max_value:
                max_value = a
                max_info = info
        return max_value, max_info["main"]
        # logger.debug(max(value))


if __name__ == "__main__":
    f = FuzzMatch()
    value, title = f.find_max_name("辉夜大小姐想让我告白")
    print(value,title)