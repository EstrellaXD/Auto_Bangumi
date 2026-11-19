"""Bangumi.tv 日历的放送日匹配（match_weekday）。"""

from module.parser.analyser.bgm_calendar import match_weekday

CALENDAR = [
    {"name": "Sousou no Frieren", "name_cn": "葬送的芙莉莲", "air_weekday": 4},
    {"name": "Kusuriya no Hitorigoto", "name_cn": "药屋少女的呢喃", "air_weekday": 5},
]


def test_substring_match_still_works():
    assert match_weekday("葬送的芙莉莲 第二季", "", CALENDAR) == 4


def test_empty_titles_do_not_match_first_item():
    """标题为空时 `"" in name_cn` 恒为真，之前会拿到日历里第一部番剧的放送日。"""
    assert match_weekday("", "", CALENDAR) is None
    assert match_weekday("  ", "  ", CALENDAR) is None
