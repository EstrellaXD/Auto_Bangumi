from thefuzz import fuzz
import logging

logger = logging.getLogger(__name__)


class FuzzMatch:
    def __init__(self, anidb_data):
        self.match_data = anidb_data

    def match(self, title, info):
        compare_value = []
        for type in ["main", "en", "ja", "zh-Hans", "zh-Hant"]:
            if info[type] is not None:
                a = fuzz.ratio(title.replace(" ", "").lower(), info[type].replace(" ", "").lower())
                compare_value.append(a)
        for compare in info["other"]:
            a = fuzz.ratio(title.replace(" ", "").lower(), compare.replace(" ", "").lower())
            compare_value.append(a)
        return max(compare_value)

    def find_max_name(self, title):
        value = []
        for info in self.match_data:
            a = self.match(title, info)
            value.append([a, info])
        logger.debug(max(value))
        return max(value)
