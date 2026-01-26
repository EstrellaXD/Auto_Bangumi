"""Test data factories for creating model instances with sensible defaults."""

from datetime import datetime

from module.models import Bangumi, RSSItem, Torrent
from module.models.config import Config
from module.models.passkey import Passkey


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


def make_config(**overrides) -> Config:
    """Create a Config instance with sensible test defaults."""
    config = Config()
    for key, value in overrides.items():
        if hasattr(config, key):
            setattr(config, key, value)
    return config


def make_passkey(**overrides) -> Passkey:
    """Create a Passkey instance with sensible test defaults."""
    defaults = dict(
        id=1,
        user_id=1,
        name="Test Passkey",
        credential_id="test_credential_id_base64url",
        public_key="test_public_key_base64",
        sign_count=0,
        aaguid="00000000-0000-0000-0000-000000000000",
        transports='["internal"]',
        created_at=datetime.utcnow(),
        last_used_at=None,
        backup_eligible=False,
        backup_state=False,
    )
    defaults.update(overrides)
    return Passkey(**defaults)
