from __future__ import annotations

from unittest.mock import patch

import pytest

from module.conf import settings
from module.models import Movie, Torrent
from module.models.config import LLM
from module.rss.analyser import RSSAnalyser
from test.factories import make_rss_item


@pytest.mark.parametrize("reverse", (False, True))
async def test_feed_keeps_episode_special_and_movie_with_same_title(
    reverse: bool,
) -> None:
    torrents = [
        Torrent(
            name="[Group] Shared Anime - 01 [1080p WEB-DL]",
            url="https://example.com/episode",
        ),
        Torrent(
            name="[Group] Shared Anime OVA01 [1080p WEB-DL]",
            url="https://example.com/ova",
        ),
        Torrent(
            name="[Group] Shared Anime Movie [1080p WEB-DL]",
            url="https://example.com/movie",
        ),
    ]
    if reverse:
        torrents.reverse()

    rss = make_rss_item(parser="none")
    with patch.object(settings, "llm", LLM(enable=False)):
        bangumi, movies = await RSSAnalyser().torrents_to_data(torrents, rss)

    assert {(item.episode_type, item.season) for item in bangumi} == {
        ("episode", 1),
        ("special", 0),
    }
    assert len(movies) == 1
    assert isinstance(movies[0], Movie)
    assert {item.title_raw for item in bangumi} == {"Shared Anime"}
    assert {item.title_raw for item in movies} == {"Shared Anime"}
