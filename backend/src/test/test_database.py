import json

import pytest
from sqlmodel import Session, SQLModel, create_engine

from module.database.bangumi import BangumiDatabase
from module.database.rss import RSSDatabase
from module.database.torrent import TorrentDatabase
from module.models import Bangumi, RSSItem, Torrent

# sqlite sync engine for testing
engine = create_engine("sqlite://", echo=False)


@pytest.fixture
def db_session():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


def test_bangumi_database(db_session):
    test_data = Bangumi(
        official_title="无职转生，到了异世界就拿出真本事",
        year="2021",
        title_raw="Mushoku Tensei",
        season=1,
        season_raw="",
        group_name="Lilith-Raws",
        dpi="1080p",
        source="Baha",
        subtitle="CHT",
        eps_collect=False,
        offset=0,
        filter="720p,\\d+-\\d+",
        rss_link="test",
        poster_link="/test/test.jpg",
        added=False,
        rule_name=None,
        save_path="downloads/无职转生，到了异世界就拿出真本事/Season 1",
        deleted=False,
    )
    db = BangumiDatabase(db_session)

    # insert
    db.add(test_data)
    result = db.search_id(1)
    assert result.official_title == test_data.official_title

    # update
    test_data.official_title = "无职转生，到了异世界就拿出真本事II"
    db.update(test_data)
    result = db.search_id(1)
    assert result.official_title == test_data.official_title

    # search poster
    poster = db.match_poster("无职转生，到了异世界就拿出真本事II (2021)")
    assert poster == "/test/test.jpg"

    # match torrent
    result = db.match_torrent(
        "[Lilith-Raws] 无职转生，到了异世界就拿出真本事 / Mushoku Tensei - 11 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4]"
    )
    assert result.official_title == "无职转生，到了异世界就拿出真本事II"

    # delete
    db.delete_one(1)
    result = db.search_id(1)
    assert result is None


def test_torrent_database(db_session):
    test_data = Torrent(
        name="[Sub Group]test S02 01 [720p].mkv",
        url="https://test.com/test.mkv",
    )
    db = TorrentDatabase(db_session)

    # insert
    db.add(test_data)
    result = db.search(1)
    assert result.name == test_data.name

    # update
    test_data.downloaded = True
    db.update(test_data)
    result = db.search(1)
    assert result.downloaded == True


def test_rss_database(db_session):
    rss_url = "https://test.com/test.xml"
    db = RSSDatabase(db_session)

    db.add(RSSItem(url=rss_url, name="Test RSS"))
    result = db.search_id(1)
    assert result.url == rss_url


# ---------------------------------------------------------------------------
# TorrentDatabase qb_hash methods
# ---------------------------------------------------------------------------


def test_torrent_search_by_qb_hash(db_session):
    """Test searching torrent by qBittorrent hash."""
    db = TorrentDatabase(db_session)

    # Create torrent with qb_hash
    torrent = Torrent(
        name="[SubGroup] Test Anime - 01 [1080p].mkv",
        url="https://example.com/torrent1",
        qb_hash="abc123def456",
    )
    db.add(torrent)

    # Search by qb_hash
    result = db.search_by_qb_hash("abc123def456")
    assert result is not None
    assert result.name == torrent.name
    assert result.qb_hash == "abc123def456"


def test_torrent_search_by_qb_hash_not_found(db_session):
    """Test searching non-existent qb_hash returns None."""
    db = TorrentDatabase(db_session)

    result = db.search_by_qb_hash("nonexistent_hash")
    assert result is None


def test_torrent_search_by_url(db_session):
    """Test searching torrent by URL."""
    db = TorrentDatabase(db_session)

    url = "https://mikanani.me/Download/torrent123.torrent"
    torrent = Torrent(
        name="[SubGroup] Test Anime - 02 [1080p].mkv",
        url=url,
    )
    db.add(torrent)

    # Search by URL
    result = db.search_by_url(url)
    assert result is not None
    assert result.url == url
    assert result.name == torrent.name


def test_torrent_search_by_url_not_found(db_session):
    """Test searching non-existent URL returns None."""
    db = TorrentDatabase(db_session)

    result = db.search_by_url("https://nonexistent.com/torrent.torrent")
    assert result is None


def test_torrent_update_qb_hash(db_session):
    """Test updating qb_hash for existing torrent."""
    db = TorrentDatabase(db_session)

    # Create torrent without qb_hash
    torrent = Torrent(
        name="[SubGroup] Test Anime - 03 [1080p].mkv",
        url="https://example.com/torrent3",
    )
    db.add(torrent)
    assert torrent.qb_hash is None

    # Update qb_hash
    success = db.update_qb_hash(torrent.id, "new_hash_value")
    assert success is True

    # Verify update
    result = db.search(torrent.id)
    assert result.qb_hash == "new_hash_value"


def test_torrent_update_qb_hash_nonexistent(db_session):
    """Test updating qb_hash for non-existent torrent returns False."""
    db = TorrentDatabase(db_session)

    success = db.update_qb_hash(99999, "some_hash")
    assert success is False


def test_torrent_with_bangumi_id(db_session):
    """Test torrent with bangumi_id for offset lookup."""
    db = TorrentDatabase(db_session)

    # Create torrent linked to a bangumi
    torrent = Torrent(
        name="[SubGroup] Test Anime - 04 [1080p].mkv",
        url="https://example.com/torrent4",
        bangumi_id=42,
        qb_hash="hash_for_bangumi_42",
    )
    db.add(torrent)

    # Search and verify bangumi_id is preserved
    result = db.search_by_qb_hash("hash_for_bangumi_42")
    assert result is not None
    assert result.bangumi_id == 42


def test_torrent_qb_hash_index_efficient(db_session):
    """Test that qb_hash lookups work correctly with multiple torrents."""
    db = TorrentDatabase(db_session)

    # Add multiple torrents
    torrents = [
        Torrent(
            name=f"Torrent {i}", url=f"https://example.com/{i}", qb_hash=f"hash_{i}"
        )
        for i in range(10)
    ]
    db.add_all(torrents)

    # Verify we can find specific torrents by hash
    result = db.search_by_qb_hash("hash_5")
    assert result is not None
    assert result.name == "Torrent 5"

    result = db.search_by_qb_hash("hash_9")
    assert result is not None
    assert result.name == "Torrent 9"

    # Non-existent hash
    result = db.search_by_qb_hash("hash_100")
    assert result is None


# ============================================================
# Title Alias Tests - for mid-season naming change handling
# ============================================================


def test_add_title_alias(db_session):
    """Test adding a title alias to an existing bangumi."""
    db = BangumiDatabase(db_session)

    bangumi = Bangumi(
        official_title="Test Anime",
        title_raw="Test Anime S1",
        group_name="TestGroup",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="test",
    )
    db.add(bangumi)
    bangumi_id = db.search_all()[0].id

    # Add an alias
    result = db.add_title_alias(bangumi_id, "Test Anime Season 1")
    assert result is True

    # Verify alias was added
    updated = db.search_id(bangumi_id)
    assert updated.title_aliases is not None
    aliases = json.loads(updated.title_aliases)
    assert "Test Anime Season 1" in aliases


def test_add_title_alias_duplicate(db_session):
    """Test that adding the same alias twice is a no-op."""
    db = BangumiDatabase(db_session)

    bangumi = Bangumi(
        official_title="Test Anime",
        title_raw="Test Anime S1",
        group_name="TestGroup",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="test",
    )
    db.add(bangumi)
    bangumi_id = db.search_all()[0].id

    # Add same alias twice
    db.add_title_alias(bangumi_id, "Test Anime Season 1")
    result = db.add_title_alias(bangumi_id, "Test Anime Season 1")
    assert result is False  # Second add should be a no-op


def test_add_title_alias_same_as_title_raw(db_session):
    """Test that adding title_raw as alias is a no-op."""
    db = BangumiDatabase(db_session)

    bangumi = Bangumi(
        official_title="Test Anime",
        title_raw="Test Anime S1",
        group_name="TestGroup",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="test",
    )
    db.add(bangumi)
    bangumi_id = db.search_all()[0].id

    result = db.add_title_alias(bangumi_id, "Test Anime S1")
    assert result is False


def test_match_torrent_with_alias(db_session):
    """Test that match_torrent finds bangumi using aliases."""
    db = BangumiDatabase(db_session)

    bangumi = Bangumi(
        official_title="Test Anime",
        title_raw="Test Anime S1",
        group_name="TestGroup",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="test",
        deleted=False,
    )
    db.add(bangumi)
    bangumi_id = db.search_all()[0].id

    # Add alias
    db.add_title_alias(bangumi_id, "Test Anime Season 1")

    # Match using title_raw
    result = db.match_torrent("[TestGroup] Test Anime S1 - 01.mkv")
    assert result is not None
    assert result.official_title == "Test Anime"

    # Match using alias
    result = db.match_torrent("[TestGroup] Test Anime Season 1 - 01.mkv")
    assert result is not None
    assert result.official_title == "Test Anime"


def test_find_semantic_duplicate_same_official_title(db_session):
    """Test finding semantic duplicates with same official title."""
    db = BangumiDatabase(db_session)

    # Add first bangumi
    bangumi1 = Bangumi(
        official_title="Frieren",
        title_raw="Sousou no Frieren",
        group_name="LoliHouse",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="test1",
    )
    db.add(bangumi1)

    # Create a semantically similar bangumi (same anime, group changed naming)
    bangumi2 = Bangumi(
        official_title="Frieren",
        title_raw="Frieren Beyond Journey's End",  # Different title_raw
        group_name="LoliHouse&动漫国",  # Group changed mid-season
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="test2",
    )

    # Should find semantic duplicate
    result = db.find_semantic_duplicate(bangumi2)
    assert result is not None
    assert result.title_raw == "Sousou no Frieren"


def test_find_semantic_duplicate_no_match_different_resolution(db_session):
    """Test that different resolution is NOT a semantic match."""
    db = BangumiDatabase(db_session)

    bangumi1 = Bangumi(
        official_title="Frieren",
        title_raw="Sousou no Frieren",
        group_name="LoliHouse",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="test1",
    )
    db.add(bangumi1)

    # Same anime but different resolution - should NOT be semantic duplicate
    bangumi2 = Bangumi(
        official_title="Frieren",
        title_raw="Sousou no Frieren 4K",
        group_name="LoliHouse",
        dpi="2160p",  # Different resolution
        source="Web",
        subtitle="CHT",
        rss_link="test2",
    )

    result = db.find_semantic_duplicate(bangumi2)
    assert result is None


def test_add_with_semantic_duplicate_creates_alias(db_session):
    """Test that adding a semantic duplicate creates an alias instead."""
    db = BangumiDatabase(db_session)

    # Add first bangumi
    bangumi1 = Bangumi(
        official_title="Frieren",
        title_raw="Sousou no Frieren",
        group_name="LoliHouse",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="test1",
    )
    db.add(bangumi1)
    initial_count = len(db.search_all())
    assert initial_count == 1

    # Try to add semantic duplicate
    bangumi2 = Bangumi(
        official_title="Frieren",
        title_raw="Frieren Beyond Journey's End",
        group_name="LoliHouse&动漫国",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="test2",
    )
    result = db.add(bangumi2)
    assert result is False  # Should not add new entry

    # Count should still be 1
    final_count = len(db.search_all())
    assert final_count == 1

    # But the new title_raw should be an alias
    original = db.search_all()[0]
    aliases = json.loads(original.title_aliases) if original.title_aliases else []
    assert "Frieren Beyond Journey's End" in aliases


def test_groups_are_similar():
    """Test group name similarity detection."""
    from module.database.bangumi import _groups_are_similar

    # Exact match
    assert _groups_are_similar("LoliHouse", "LoliHouse") is True

    # Substring match (one contains the other)
    assert _groups_are_similar("LoliHouse", "LoliHouse&动漫国字幕组") is True
    assert _groups_are_similar("LoliHouse&动漫国字幕组", "LoliHouse") is True

    # Completely different groups
    assert _groups_are_similar("LoliHouse", "Sakurato") is False
    assert _groups_are_similar("字幕组A", "字幕组B") is False

    # Edge cases
    assert _groups_are_similar(None, "LoliHouse") is False
    assert _groups_are_similar("LoliHouse", None) is False
    assert _groups_are_similar(None, None) is False


def test_get_all_title_patterns(db_session):
    """Test getting all title patterns for a bangumi."""
    db = BangumiDatabase(db_session)

    bangumi = Bangumi(
        official_title="Test Anime",
        title_raw="Test Anime S1",
        group_name="TestGroup",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="test",
    )
    db.add(bangumi)
    bangumi_id = db.search_all()[0].id

    # Add aliases
    db.add_title_alias(bangumi_id, "Test Anime Season 1")
    db.add_title_alias(bangumi_id, "TA S1")

    # Get all patterns
    updated = db.search_id(bangumi_id)
    patterns = db.get_all_title_patterns(updated)

    assert len(patterns) == 3
    assert "Test Anime S1" in patterns
    assert "Test Anime Season 1" in patterns
    assert "TA S1" in patterns


def test_match_list_with_aliases(db_session):
    """Test match_list works with aliases."""
    db = BangumiDatabase(db_session)

    bangumi = Bangumi(
        official_title="Test Anime",
        title_raw="Test Anime S1",
        group_name="TestGroup",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="rss1",
    )
    db.add(bangumi)
    bangumi_id = db.search_all()[0].id
    db.add_title_alias(bangumi_id, "Test Anime Season 1")

    # Create torrents with different naming patterns
    torrents = [
        Torrent(name="[TestGroup] Test Anime S1 - 01.mkv", url="url1"),
        Torrent(name="[TestGroup] Test Anime Season 1 - 02.mkv", url="url2"),
        Torrent(name="[OtherGroup] Different Anime - 01.mkv", url="url3"),
    ]

    # Only the third torrent should be unmatched
    unmatched = db.match_list(torrents, "rss2")
    assert len(unmatched) == 1
    assert unmatched[0].name == "[OtherGroup] Different Anime - 01.mkv"
