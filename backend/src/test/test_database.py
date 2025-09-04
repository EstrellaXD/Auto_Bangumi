from module.database.combine import Database
from module.models import Bangumi, RSSItem, Torrent
from sqlmodel import create_engine
from sqlmodel.pool import StaticPool

# sqlite mock engine
engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


def test_database_combine_bangumi_to_rss():
    """Test bangumi_to_rss functionality"""
    rss_data = RSSItem(
        name="Test RSS Feed",
        url="https://test.com/rss.xml",
        aggregate=True,
        parser="mikan",
        enabled=True,
    )

    bangumi_data = Bangumi(
        official_title="Test Bangumi",
        title_raw="Test Title",
        season=1,
        rss_link="https://test.com/rss.xml",
    )

    with Database(engine) as db:
        db.create_table()

        # Add RSS and Bangumi
        db.rss.add(rss_data)
        db.bangumi.add(bangumi_data)

        # Test bangumi_to_rss
        found_rss = db.bangumi_to_rss(bangumi_data)
        assert found_rss is not None
        assert found_rss.url == "https://test.com/rss.xml"
        assert found_rss.name == "Test RSS Feed"

        # Test with non-existent RSS link
        bangumi_no_rss = Bangumi(
            official_title="No RSS Bangumi",
            title_raw="No RSS Title",
            season=1,
            rss_link="https://nonexistent.com/rss.xml",
        )
        found_rss_none = db.bangumi_to_rss(bangumi_no_rss)
        assert found_rss_none is None


def test_database_combine_torrent_to_bangumi():
    """Test torrent_to_bangumi functionality"""
    # Create a new engine for this test to avoid interference
    test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    bangumi_data = Bangumi(
        official_title="Test Bangumi",
        title_raw="Test Title",
        season=2,
        rss_link="https://test.com/rss.xml",
    )

    torrent_data = Torrent(
        name="[Group]Test Bangumi S02 E01",
        url="https://test.com/torrent1.torrent",
        bangumi_official_title="Test Bangumi",
        bangumi_season=2,
        rss_link="https://test.com/rss.xml",
    )

    with Database(test_engine) as db:
        db.create_table()

        # Add Bangumi and Torrent
        db.bangumi.add(bangumi_data)
        db.torrent.add(torrent_data)

        # Test torrent_to_bangumi
        found_bangumi = db.torrent_to_bangumi(torrent_data)
        assert found_bangumi is not None
        assert found_bangumi.official_title == "Test Bangumi"
        assert found_bangumi.season == 2
        assert found_bangumi.rss_link == "https://test.com/rss.xml"

        # Test with non-existent bangumi
        torrent_no_bangumi = Torrent(
            name="[Group]Nonexistent S01 E01",
            url="https://test.com/torrent_no_bangumi.torrent",
            bangumi_official_title="Nonexistent Bangumi",
            bangumi_season=1,
            rss_link="https://nonexistent.com/rss.xml",
        )
        found_bangumi_none = db.torrent_to_bangumi(torrent_no_bangumi)
        assert found_bangumi_none is None


def test_database_combine_find_torrent_by_bangumi():
    """Test find_torrent_by_bangumi functionality"""
    bangumi_data = Bangumi(
        official_title="Test Bangumi",
        title_raw="Test Title",
        season=1,
        rss_link="https://test.com/rss.xml",
    )

    torrents = [
        Torrent(
            name="[Group]Test Bangumi S01 E01",
            url="https://test.com/torrent1.torrent",
            bangumi_official_title="Test Bangumi",
            bangumi_season=1,
            rss_link="https://test.com/rss.xml",
        ),
        Torrent(
            name="[Group]Test Bangumi S01 E02",
            url="https://test.com/torrent2.torrent",
            bangumi_official_title="Test Bangumi",
            bangumi_season=1,
            rss_link="https://test.com/rss.xml",
        ),
        Torrent(
            name="[Group]Other Bangumi S01 E01",
            url="https://test.com/torrent3.torrent",
            bangumi_official_title="Other Bangumi",
            bangumi_season=1,
            rss_link="https://test.com/other_rss.xml",
        ),
    ]

    with Database(engine) as db:
        db.create_table()

        # Add Bangumi and Torrents
        db.bangumi.add(bangumi_data)
        for torrent in torrents:
            db.torrent.add(torrent)

        # Test find_torrent_by_bangumi
        found_torrents = db.find_torrent_by_bangumi(bangumi_data)
        assert len(found_torrents) == 2
        assert all(t.bangumi_official_title == "Test Bangumi" for t in found_torrents)
        assert all(t.bangumi_season == 1 for t in found_torrents)

        # Test with bangumi that has no torrents
        bangumi_no_torrents = Bangumi(
            official_title="No Torrents Bangumi",
            title_raw="No Torrents",
            season=1,
            rss_link="https://no-torrents.com/rss.xml",
        )
        found_torrents_none = db.find_torrent_by_bangumi(bangumi_no_torrents)
        assert len(found_torrents_none) == 0


def test_database_combine_get_unrenamed_torrents():
    """Test get_unrenamed_torrents functionality"""
    torrents = [
        Torrent(
            name="Downloaded and Renamed",
            url="https://test.com/renamed.torrent",
            downloaded=True,
            renamed=True,
        ),
        Torrent(
            name="Downloaded but Not Renamed 1",
            url="https://test.com/not_renamed1.torrent",
            downloaded=True,
            renamed=False,
        ),
        Torrent(
            name="Downloaded but Not Renamed 2",
            url="https://test.com/not_renamed2.torrent",
            downloaded=True,
            renamed=False,
        ),
        Torrent(
            name="Not Downloaded",
            url="https://test.com/not_downloaded.torrent",
            downloaded=False,
            renamed=False,
        ),
    ]

    with Database(engine) as db:
        db.create_table()

        # Add torrents
        for torrent in torrents:
            db.torrent.add(torrent)

        # Test get_unrenamed_torrents
        unrenamed = db.get_unrenamed_torrents()
        assert len(unrenamed) == 2
        assert all(t.downloaded is True for t in unrenamed)
        assert all(t.renamed is False for t in unrenamed)
        torrent_names = [t.name for t in unrenamed]
        assert "Downloaded but Not Renamed 1" in torrent_names
        assert "Downloaded but Not Renamed 2" in torrent_names


def test_database_combine_find_bangumi_by_name_aggregated():
    """Test find_bangumi_by_name with aggregated=True"""
    bangumi_data = Bangumi(
        official_title="Test Bangumi",
        title_raw="Original Title,Alternative Title,Third Title",
        season=1,
        rss_link="https://test.com/rss.xml",
        deleted=False,
    )

    with Database(engine) as db:
        db.create_table()
        db.bangumi.add(bangumi_data)

        # Test finding by partial title_raw (aggregated=True)
        found_bangumi = db.find_bangumi_by_name("Alternative Title", "any_rss", True)
        assert found_bangumi is not None
        assert found_bangumi.official_title == "Test Bangumi"

        # Test finding by another partial title_raw
        found_bangumi2 = db.find_bangumi_by_name("Third Title", "any_rss", True)
        assert found_bangumi2 is not None
        assert found_bangumi2.official_title == "Test Bangumi"

        # Test not finding non-existent title
        found_bangumi_none = db.find_bangumi_by_name("Nonexistent Title", "any_rss", True)
        assert found_bangumi_none is None


def test_database_combine_find_bangumi_by_name_not_aggregated():
    """Test find_bangumi_by_name with aggregated=False"""
    bangumi_data = Bangumi(
        official_title="Test Bangumi",
        title_raw="Test Title",
        season=1,
        rss_link="https://test.com/specific_rss.xml",
        deleted=False,
    )

    with Database(engine) as db:
        db.create_table()
        db.bangumi.add(bangumi_data)

        # Test finding by RSS link (aggregated=False)
        found_bangumi = db.find_bangumi_by_name("any_name", "https://test.com/specific_rss.xml", False)
        assert found_bangumi is not None
        assert found_bangumi.official_title == "Test Bangumi"

        # Test not finding with wrong RSS link
        found_bangumi_none = db.find_bangumi_by_name("any_name", "https://wrong.com/rss.xml", False)
        assert found_bangumi_none is None


def test_database_combine_table_management():
    """Test table creation and deletion"""
    # Create a new engine for this test to avoid interference
    test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    with Database(test_engine) as db:
        # Test create_table
        db.create_table()

        # Add some data to verify tables exist
        rss_data = RSSItem(name="Test", url="https://test.com/table_test_rss.xml")
        bangumi_data = Bangumi(official_title="Test Table", title_raw="Test Table", season=1, rss_link="test_table")
        torrent_data = Torrent(name="Test Table", url="https://test.com/table_test_torrent")

        db.rss.add(rss_data)
        db.bangumi.add(bangumi_data)
        db.torrent.add(torrent_data)

        # Verify data exists
        assert len(db.rss.search_all()) == 1
        assert len(db.bangumi.search_all()) == 1
        assert len(db.torrent.search_all()) == 1

        # Test drop_table
        db.drop_table()

        # Recreate tables (should be empty)
        db.create_table()
        assert len(db.rss.search_all()) == 0
        assert len(db.bangumi.search_all()) == 0
        assert len(db.torrent.search_all()) == 0


def test_database_combine_deleted_bangumi_filter():
    """Test that deleted bangumi are properly filtered in find_bangumi_by_name"""
    active_bangumi = Bangumi(
        official_title="Active Bangumi",
        title_raw="Active Title",
        season=1,
        rss_link="https://test.com/active_rss.xml",
        deleted=False,
    )

    deleted_bangumi = Bangumi(
        official_title="Deleted Bangumi",
        title_raw="Deleted Title",
        season=1,
        rss_link="https://test.com/deleted_rss.xml",
        deleted=True,
    )

    with Database(engine) as db:
        db.create_table()
        db.bangumi.add(active_bangumi)
        db.bangumi.add(deleted_bangumi)

        # Test non-aggregated search should not find deleted bangumi
        found_active = db.find_bangumi_by_name("any_name", "https://test.com/active_rss.xml", False)
        assert found_active is not None
        assert found_active.official_title == "Active Bangumi"

        found_deleted = db.find_bangumi_by_name("any_name", "https://test.com/deleted_rss.xml", False)
        assert found_deleted is None  # Should not find deleted bangumi
