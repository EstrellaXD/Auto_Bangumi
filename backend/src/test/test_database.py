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
        Torrent(name=f"Torrent {i}", url=f"https://example.com/{i}", qb_hash=f"hash_{i}")
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
