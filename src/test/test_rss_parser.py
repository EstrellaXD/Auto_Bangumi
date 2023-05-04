from module.models import Config
from module.core.api_func import RSSAnalyser


def test_rss_analyser():
    settings = Config()
    rss_analyser = RSSAnalyser(settings)
    url = "https://mikanani.me/RSS/Bangumi?bangumiId=2966&subgroupid=552"

    data = rss_analyser.rss_to_data(url=url)

    assert data.title_raw == "Yamada-kun to Lv999 no Koi wo Suru"
    assert data.official_title == "和山田谈场 Lv999 的恋爱"
    assert data.season == 1

    url = "http://dmhy.org/topics/rss/rss.xml?keyword=假面骑士+Geats&sort_id=0&team_id=648&order=date-desc"
    data = rss_analyser.rss_to_data(url=url)

    assert data.title_raw == "假面骑士Geats"
    assert data.official_title == "假面骑士Geats"
    assert data.season == 1
