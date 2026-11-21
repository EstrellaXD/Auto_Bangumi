from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pytest

from module.conf import settings
from module.models import Movie, RSSItem, Torrent
from module.models.config import LLM
from module.parser.analyser import selector
from module.parser.analyser.selector import parse_configured_release_title
from module.parser.analyser.tokenizer.result import ParsedRelease
from module.rss.analyser import RSSAnalyser
from module.rss.engine import RSSEngine
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


async def test_feed_does_not_create_entry_for_mixed_collection() -> None:
    torrent = Torrent(
        name="[Group] Shared Anime：TV+OVA+Manga+Music [1080p WEB-DL]",
        url="https://example.com/mixed",
    )

    rss = make_rss_item(parser="none")
    with (
        patch.object(settings, "llm", LLM(enable=False)),
        patch.object(settings.rss_parser, "engine", "tokenizer"),
    ):
        bangumi, movies = await RSSAnalyser().torrents_to_data([torrent], rss)

    assert bangumi == []
    assert movies == []


async def test_rss_to_data_keeps_one_parser_engine_across_awaits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A settings reload must not split one RSS workflow across engines."""
    parser_config = SimpleNamespace(engine="classic")
    monkeypatch.setattr(
        selector,
        "settings",
        SimpleNamespace(rss_parser=parser_config),
    )

    classic_release = ParsedRelease(raw="resource", title_en="Classic")
    preview_release = ParsedRelease(raw="resource", title_en="Preview")
    monkeypatch.setattr(
        selector.classic,
        "parse_release_title",
        lambda raw: classic_release,
    )
    monkeypatch.setattr(
        selector.preview,
        "parse_release_title",
        lambda raw: preview_release,
    )

    torrent = Torrent(name="resource", url="https://example.com/resource")
    analyser = RSSAnalyser()

    async def check_new(torrents, rss: RSSItem | None = None):
        return torrents

    async def match_movies(torrents, rss_link: str):
        assert parse_configured_release_title(torrent.name) is classic_release
        parser_config.engine = "tokenizer"
        await asyncio.sleep(0)
        assert parse_configured_release_title(torrent.name) is classic_release
        return torrents

    async def match_bangumi(torrents, rss_link: str, match_datas):
        assert parse_configured_release_title(torrent.name) is classic_release
        return torrents

    async def torrents_to_data(torrents, rss, full_parse: bool = True):
        assert parse_configured_release_title(torrent.name) is classic_release
        return [], []

    monkeypatch.setattr(analyser, "torrents_to_data", torrents_to_data)
    engine = cast(
        RSSEngine,
        SimpleNamespace(
            db=SimpleNamespace(
                torrent=SimpleNamespace(check_new=check_new),
                movie=SimpleNamespace(match_list=match_movies),
                bangumi=SimpleNamespace(match_list=match_bangumi),
            )
        ),
    )

    await analyser.rss_to_data(make_rss_item(parser="none"), [torrent], engine, [])

    # The task-local scope is gone, so a later workflow sees the new setting.
    assert parse_configured_release_title(torrent.name) is preview_release


@pytest.mark.parametrize("engine", ["tokenizer", "classic"])
async def test_explicit_rss_previews_range_with_configured_exclusions(
    monkeypatch, engine
):
    from xml.etree.ElementTree import fromstring

    from module.models import Bangumi, ResponseModel
    from module.network import RequestContent
    from module.parser.release_policy import is_offset_signal, preference_identity

    title = "[Group] Example Show [01-06 合集][WebRip 1080p]"
    xml = fromstring(f"""<rss><channel><item><title>{title}</title>
        <link>https://example.com/episode</link>
        <enclosure url="https://example.com/file.torrent" type="application/x-bittorrent" />
        </item></channel></rss>""")

    async def get_xml(*args, **kwargs):
        return xml

    monkeypatch.setattr(RequestContent, "get_xml", get_xml)
    monkeypatch.setattr(settings.rss_parser, "engine", engine)
    rss = make_rss_item(parser="none")
    analyser = RSSAnalyser()
    for exclusions in ([r"\d+-\d+"], ["720", r"1080p"]):
        monkeypatch.setattr(settings.rss_parser, "filter", exclusions)
        rejected = await analyser.link_to_data(rss)
        assert isinstance(rejected, ResponseModel)
        assert rejected.msg_en == "Cannot find any torrent."

    for exclusions in ([], ["720"]):
        monkeypatch.setattr(settings.rss_parser, "filter", exclusions)
        rule = await analyser.link_to_data(rss)
        assert isinstance(rule, Bangumi)
        assert rule.title_raw == "Example Show"
        assert rule.rss_link == rss.url
        assert rule.filter == ",".join(exclusions)
        assert rule.eps_collect
    release = parse_configured_release_title(title)
    assert release is not None
    assert preference_identity(release) is None
    assert not is_offset_signal(release)


async def test_explicit_rss_rejects_mixed_collection_and_unnumbered_batch():
    analyser = RSSAnalyser()
    rss = make_rss_item(parser="none")
    for title in ("Anime Title [TV 01-12 + OVA 01-02]", "Anime Title Complete Batch"):
        assert (
            await analyser.torrent_to_data(
                Torrent(name=f"[Group] {title} [1080p]"), rss, allow_episode_range=True
            )
            is None
        )
