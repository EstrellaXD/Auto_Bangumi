from thefuzz import fuzz
import logging
from module.utils import json_config
from module.conf import settings

logger = logging.getLogger(__name__)


class FuzzMatch:
    def __init__(self):
        # FIXME: settings has no anidb_*
        try:
            anidb_data = json_config.get(settings.anidb_url)
            json_config.save(settings.anidb_path, anidb_data)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.debug(e)
            logger.info(f"Fail to get anidb data, reading local data")
            anidb_data = json_config.load(settings.anidb_path)
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
