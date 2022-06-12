from thefuzz import fuzz
import logging
from utils import json_config
from conf import settings

logger = logging.getLogger(__name__)


class FuzzMatch:
    def __init__(self):
        try:
            anidb_data = json_config.get(settings.anidb_url)
            json_config.save("anidb.json", anidb_data)
        except Exception as e:
            logger.debug(e)
            logger.info(f"Fail to get anidb data, reading local data")
            anidb_data = json_config.load("anidb.json")
        self.match_data = anidb_data

    @staticmethod
    def match(title_raw, info: dict):
        compare_value = []
        for tag in ["main", "en", "ja", "zh-Hans", "zh-Hant"]:
            if info[tag] is not None:
                a = fuzz.token_sort_ratio(title_raw.lower(), info[tag].lower())
                compare_value.append(a)
        for compare in info["other"]:
            a = fuzz.token_sort_ratio(title_raw.lower(), compare.lower())
            compare_value.append(a)
        return max(compare_value)

    def find_max_name(self, title_raw):
        max_value = 0
        max_info = None
        for info in self.match_data:
            a = self.match(title_raw, info)
            if a > max_value:
                max_value = a
                max_info = info
        return max_value, max_info["main"]
        # logger.debug(max(value))


if __name__ == "__main__":
    from const_dev import DEV_SETTINGS
    settings.init(DEV_SETTINGS)
    f = FuzzMatch()
    name = "勇者、辞职不干了"
    value, title = f.find_max_name(name)
    print(f"Raw    Name: {name} \n"
          f"Match  Name: {title} \n"
          f"Match Value: {value}")
