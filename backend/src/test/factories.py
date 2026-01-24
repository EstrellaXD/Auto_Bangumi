"""Test data factories for creating model instances with sensible defaults."""

from module.models import Bangumi, RSSItem, Torrent


def make_bangumi(**overrides) -> Bangumi:
    """Create a Bangumi instance with sensible test defaults."""
    defaults = dict(
        official_title="Test Anime",
        year="2024",
        title_raw="Test Anime Raw",
        season=1,
        season_raw="",
        group_name="TestGroup",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        eps_collect=False,
        offset=0,
        filter="720",
        rss_link="https://mikanani.me/RSS/test",
        poster_link="/test/poster.jpg",
        added=True,
        rule_name="[TestGroup] Test Anime S1",
        save_path="/downloads/Bangumi/Test Anime (2024)/Season 1",
        deleted=False,
    )
    defaults.update(overrides)
    return Bangumi(**defaults)


def make_torrent(**overrides) -> Torrent:
    """Create a Torrent instance with sensible test defaults."""
    defaults = dict(
        name="[TestGroup] Test Anime Raw - 01 [1080p].mkv",
        url="https://example.com/test.torrent",
        homepage="https://mikanani.me/Home/Episode/test",
        downloaded=False,
    )
    defaults.update(overrides)
    return Torrent(**defaults)


def make_rss_item(**overrides) -> RSSItem:
    """Create an RSSItem instance with sensible test defaults."""
    defaults = dict(
        name="Test RSS Feed",
        url="https://mikanani.me/RSS/MyBangumi?token=test",
        aggregate=True,
        parser="mikan",
        enabled=True,
    )
    defaults.update(overrides)
    return RSSItem(**defaults)
