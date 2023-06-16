from module.parser.analyser.tmdb_parser import tmdb_parser


def test_tmdb_parser():
    bangumi_title = "海盗战记"
    bangumi_year = "2019"
    bangumi_season = 2

    tmdb_info = tmdb_parser(bangumi_title, "zh")

    assert tmdb_info.title == "冰海战记"
    assert tmdb_info.year == bangumi_year
    assert tmdb_info.last_season == bangumi_season
