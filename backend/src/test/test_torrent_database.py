from module.database.combine import Database
from module.models import Torrent
from sqlmodel import create_engine
from sqlmodel.pool import StaticPool


def create_test_engine():
    """Create a new in-memory SQLite engine for each test"""
    return create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )


def test_torrent_database_add():
    test_data = Torrent(
        name="[Sub Group]test S02 01 [720p].mkv",
        url="https://test.com/test.mkv",
        bangumi_official_title="Test Bangumi",
        bangumi_season=2,
        rss_link="https://test.com/rss",
    )
    with Database(create_test_engine()) as db:
        db.create_table()
        
        # Test add
        db.torrent.add(test_data)
        torrent = db.torrent.search_by_url(test_data.url)
        assert torrent is not None
        assert torrent.name == test_data.name
        assert torrent.url == test_data.url
        assert torrent.downloaded is False
        assert torrent.renamed is False


def test_torrent_database_update():
    test_data = Torrent(
        name="[Sub Group]test S02 01 [720p].mkv",
        url="https://test.com/update_test.mkv",
        downloaded=False,
        renamed=False,
    )
    
    with Database(create_test_engine()) as db:
        db.create_table()
        db.torrent.add(test_data)
        
        # Test update via add (merge)
        test_data.downloaded = True
        test_data.renamed = True
        test_data.download_uid = "test_uid_123"
        
        db.torrent.add(test_data)
        updated_torrent = db.torrent.search_by_url(test_data.url)
        assert updated_torrent is not None
        assert updated_torrent.downloaded is True
        assert updated_torrent.renamed is True
        assert updated_torrent.download_uid == "test_uid_123"


def test_torrent_database_search():
    test_data = Torrent(
        name="[Group]Test Bangumi S01 E01",
        url="https://test.com/search_test.torrent",
        download_uid="uid_12345",
        bangumi_official_title="Test Bangumi",
        bangumi_season=1,
        rss_link="https://test.com/rss",
        downloaded=True,
        renamed=False,
    )
    
    with Database(create_test_engine()) as db:
        db.create_table()
        db.torrent.add(test_data)
        
        # Test search_by_url
        torrent_by_url = db.torrent.search_by_url(test_data.url)
        assert torrent_by_url is not None
        assert torrent_by_url.name == test_data.name
        
        # Test search_by_duid
        torrent_by_duid = db.torrent.search_by_duid("uid_12345")
        assert torrent_by_duid is not None
        assert torrent_by_duid.url == test_data.url
        
        # Test search_all
        all_torrents = db.torrent.search_all()
        assert len(all_torrents) == 1
        assert all_torrents[0].name == test_data.name


def test_torrent_database_filter_by_bangumi():
    torrents = [
        Torrent(
            name="[Group]Bangumi A S01 E01",
            url="https://test.com/bangumi_a_e01.torrent",
            bangumi_official_title="Bangumi A",
            bangumi_season=1,
            rss_link="https://test.com/rss_a",
        ),
        Torrent(
            name="[Group]Bangumi A S01 E02",
            url="https://test.com/bangumi_a_e02.torrent", 
            bangumi_official_title="Bangumi A",
            bangumi_season=1,
            rss_link="https://test.com/rss_a",
        ),
        Torrent(
            name="[Group]Bangumi B S01 E01",
            url="https://test.com/bangumi_b_e01.torrent",
            bangumi_official_title="Bangumi B",
            bangumi_season=1,
            rss_link="https://test.com/rss_b",
        ),
    ]
    
    with Database(create_test_engine()) as db:
        db.create_table()
        
        for torrent in torrents:
            db.torrent.add(torrent)
        
        # Test filter_by_bangumi
        bangumi_a_torrents = db.torrent.filter_by_bangumi("Bangumi A", 1, "https://test.com/rss_a")
        assert len(bangumi_a_torrents) == 2
        
        bangumi_b_torrents = db.torrent.filter_by_bangumi("Bangumi B", 1, "https://test.com/rss_b")
        assert len(bangumi_b_torrents) == 1
        
        # Test non-existent bangumi
        nonexistent_torrents = db.torrent.filter_by_bangumi("Nonexistent", 1, "https://test.com/rss")
        assert len(nonexistent_torrents) == 0


def test_torrent_database_rename_status():
    torrents = [
        Torrent(
            name="Downloaded and Renamed",
            url="https://test.com/renamed.torrent",
            downloaded=True,
            renamed=True,
        ),
        Torrent(
            name="Downloaded but Not Renamed",
            url="https://test.com/not_renamed.torrent",
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
    
    with Database(create_test_engine()) as db:
        db.create_table()
        
        for torrent in torrents:
            db.torrent.add(torrent)
        
        # Test search_all_unrenamed
        unrenamed = db.torrent.search_all_unrenamed()
        assert len(unrenamed) == 1
        assert unrenamed[0].name == "Downloaded but Not Renamed"
        
        # Test search_downloaded_unrenamed
        downloaded_unrenamed = db.torrent.search_downloaded_unrenamed()
        assert len(downloaded_unrenamed) == 1
        assert downloaded_unrenamed[0].name == "Downloaded but Not Renamed"


def test_torrent_database_check_new():
    existing_torrent = Torrent(
        name="Existing Torrent",
        url="https://test.com/existing.torrent",
        downloaded=True,
    )
    
    with Database(create_test_engine()) as db:
        db.create_table()
        db.torrent.add(existing_torrent)
        
        # Test check_new
        test_torrents = [
            Torrent(name="Existing Torrent", url="https://test.com/existing.torrent"),  # Already exists and downloaded
            Torrent(name="New Torrent 1", url="https://test.com/new1.torrent"),        # New torrent
            Torrent(name="New Torrent 2", url="https://test.com/new2.torrent"),        # New torrent
        ]
        
        new_torrents = db.torrent.check_new(test_torrents)
        assert len(new_torrents) == 2
        assert new_torrents[0].name == "New Torrent 1"
        assert new_torrents[1].name == "New Torrent 2"
        
        # Test with existing but not downloaded torrent
        not_downloaded = Torrent(
            name="Not Downloaded",
            url="https://test.com/not_downloaded.torrent",
            downloaded=False,
        )
        db.torrent.add(not_downloaded)
        
        test_torrents_2 = [
            Torrent(name="Not Downloaded", url="https://test.com/not_downloaded.torrent"),
            Torrent(name="Another New", url="https://test.com/another_new.torrent"),
        ]
        
        new_torrents_2 = db.torrent.check_new(test_torrents_2)
        assert len(new_torrents_2) == 2  # Both should be considered "new"


def test_torrent_database_delete():
    test_torrents = [
        Torrent(
            name="Test Torrent 1",
            url="https://test.com/delete1.torrent",
            download_uid="uid_001",
        ),
        Torrent(
            name="Test Torrent 2", 
            url="https://test.com/delete2.torrent",
            download_uid="uid_002",
        ),
    ]
    
    with Database(create_test_engine()) as db:
        db.create_table()
        
        for torrent in test_torrents:
            db.torrent.add(torrent)
        
        # Test delete_by_url
        delete_result1 = db.torrent.delete_by_url("https://test.com/delete1.torrent")
        assert delete_result1 is True
        
        deleted_torrent = db.torrent.search_by_url("https://test.com/delete1.torrent")
        assert deleted_torrent is None
        
        # Test delete non-existent URL
        delete_result2 = db.torrent.delete_by_url("https://test.com/nonexistent.torrent")
        assert delete_result2 is False
        
        # Test delete_by_duid
        delete_result3 = db.torrent.delete_by_duid("uid_002")
        assert delete_result3 is True
        
        deleted_by_duid = db.torrent.search_by_duid("uid_002")
        assert deleted_by_duid is None
        
        # Test delete non-existent duid
        delete_result4 = db.torrent.delete_by_duid("nonexistent_uid")
        assert delete_result4 is False


def test_torrent_database_integration():
    """Basic integration test for Torrent database operations"""
    test_data = Torrent(
        name="[Sub Group]test S02 01 [720p].mkv",
        url="https://test.com/integration_test.mkv",
    )
    with Database(create_test_engine()) as db:
        db.create_table()
        # insert
        db.torrent.add(test_data)
        torrent = db.torrent.search_by_url(test_data.url)
        assert torrent is not None
        assert torrent.name == test_data.name
        assert torrent.url == test_data.url

        # update
        test_data.downloaded = True
        db.torrent.add(test_data)
        torrent = db.torrent.search_by_url(test_data.url)
        assert torrent is not None
        assert torrent.name == test_data.name
        assert torrent.url == test_data.url
        assert torrent.downloaded is True
