import pytest

from module.parser import TitleParser
from module.rss.analyser import RSSAnalyser
from test.factories import make_bangumi, make_rss_item, make_torrent


@pytest.mark.parametrize(
    ("rss_name", "aggregate", "expected_query"),
    [
        ("TMDB Lookup Title", False, "TMDB Lookup Title"),
        ("   ", False, "Parsed Torrent Title"),
        ("Aggregate Feed Name", True, "Parsed Torrent Title"),
    ],
)
async def test_tmdb_query_prefers_non_aggregate_rss_name(
    mocker, rss_name, aggregate, expected_query
):
    tmdb_parser = mocker.patch.object(
        TitleParser,
        "tmdb_parser",
        return_value=("Resolved TMDB Title", 2, "2025", "/poster.jpg"),
    )
    bangumi = make_bangumi(
        official_title="Parsed Torrent Title",
        title_raw="Original Torrent Title",
        season=1,
    )
    rss = make_rss_item(name=rss_name, aggregate=aggregate, parser="tmdb")

    await RSSAnalyser().official_title_parser(bangumi, rss, make_torrent())

    assert tmdb_parser.await_args.args[0] == expected_query
    assert bangumi.official_title == "Resolved TMDB Title"
    assert bangumi.title_raw == "Original Torrent Title"
    assert bangumi.season == 2
    assert bangumi.year == "2025"
    assert bangumi.poster_link == "/poster.jpg"
