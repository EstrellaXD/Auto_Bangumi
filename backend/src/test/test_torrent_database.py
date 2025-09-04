from module.database.combine import Database
from module.models import Torrent
from sqlmodel import create_engine
from sqlmodel.pool import StaticPool

# 模块级别共享的 engine
TEST_ENGINE = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

# 初始化表结构
with Database(TEST_ENGINE) as db:
    db.create_table()


def test_torrent_database_add():
    # 准备所有测试数据
    test_torrent_list = [
        Torrent(
            name="[Sub Group]test S02 01 [720p].mkv",
            url="https://test.com/test1.mkv",
            bangumi_official_title="Test Bangumi",
            bangumi_season=2,
            rss_link="https://test.com/rss",
        ),
        Torrent(
            name="[Sub Group]test S02 02 [720p].mkv",
            url="https://test.com/update_test.mkv",
            downloaded=False,
            renamed=False,
        ),
        Torrent(
            name="[Group]Test Bangumi S01 E01",
            url="https://test.com/search_test.torrent",
            download_uid="uid_12345",
            bangumi_official_title="Test Bangumi",
            bangumi_season=1,
            rss_link="https://test.com/rss",
            downloaded=True,
            renamed=False,
        ),
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
        Torrent(
            name="Existing Torrent",
            url="https://test.com/existing.torrent",
            downloaded=True,
        ),
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

    with Database(TEST_ENGINE) as db:
        # 批量插入所有测试数据
        for torrent in test_torrent_list:
            db.torrent.add(torrent)

        # 验证插入成功
        all_torrents = db.torrent.search_all()
        assert len(all_torrents) == len(test_torrent_list)

        # Test basic functionality
        torrent = db.torrent.search_by_url("https://test.com/test1.mkv")
        assert torrent is not None
        assert torrent.name == "[Sub Group]test S02 01 [720p].mkv"
        assert torrent.downloaded is False
        assert torrent.renamed is False


def test_torrent_database_update():
    with Database(TEST_ENGINE) as db:
        # Find existing torrent for update test
        test_torrent = db.torrent.search_by_url("https://test.com/update_test.mkv")
        assert test_torrent is not None
        assert test_torrent.downloaded is False
        assert test_torrent.renamed is False

        # Test update via add (merge)
        updated_data = Torrent(
            name=test_torrent.name,
            url=test_torrent.url,
            downloaded=True,
            renamed=True,
            download_uid="test_uid_123",
        )

        db.torrent.add(updated_data)
        updated_torrent = db.torrent.search_by_url(updated_data.url)
        assert updated_torrent is not None
        assert updated_torrent.downloaded is True
        assert updated_torrent.renamed is True
        assert updated_torrent.download_uid == "test_uid_123"


def test_torrent_database_search():
    with Database(TEST_ENGINE) as db:
        # Test search_by_url
        torrent_by_url = db.torrent.search_by_url("https://test.com/search_test.torrent")
        assert torrent_by_url is not None
        assert torrent_by_url.name == "[Group]Test Bangumi S01 E01"

        # Test search_by_duid
        torrent_by_duid = db.torrent.search_by_duid("uid_12345")
        assert torrent_by_duid is not None
        assert torrent_by_duid.url == "https://test.com/search_test.torrent"

        # Test search_all
        all_torrents = db.torrent.search_all()
        assert len(all_torrents) >= 12  # Should have at least 12 torrents from add test


def test_torrent_database_filter_by_bangumi():
    with Database(TEST_ENGINE) as db:
        # Test filter_by_bangumi (using existing data)
        bangumi_a_torrents = db.torrent.filter_by_bangumi("Bangumi A", 1, "https://test.com/rss_a")
        assert len(bangumi_a_torrents) == 2

        bangumi_b_torrents = db.torrent.filter_by_bangumi("Bangumi B", 1, "https://test.com/rss_b")
        assert len(bangumi_b_torrents) == 1

        # Test non-existent bangumi
        nonexistent_torrents = db.torrent.filter_by_bangumi("Nonexistent", 1, "https://test.com/rss")
        assert len(nonexistent_torrents) == 0


def test_torrent_database_rename_status():
    with Database(TEST_ENGINE) as db:
        # Test search_all_unrenamed (should find torrents with renamed=False and downloaded=True)
        unrenamed = db.torrent.search_all_unrenamed()
        # Should find "Downloaded but Not Renamed" and possibly others
        unrenamed_names = [t.name for t in unrenamed]
        assert "Downloaded but Not Renamed" in unrenamed_names

        # Test search_downloaded_unrenamed
        downloaded_unrenamed = db.torrent.search_downloaded_unrenamed()
        downloaded_unrenamed_names = [t.name for t in downloaded_unrenamed]
        assert "Downloaded but Not Renamed" in downloaded_unrenamed_names
        # Should not include "Downloaded and Renamed" or "Not Downloaded"
        assert "Downloaded and Renamed" not in downloaded_unrenamed_names
        assert "Not Downloaded" not in downloaded_unrenamed_names


def test_torrent_database_check_new():
    with Database(TEST_ENGINE) as db:
        # Test check_new with existing data
        test_torrents = [
            Torrent(name="Existing Torrent", url="https://test.com/existing.torrent"),  # Already exists and downloaded
            Torrent(name="New Torrent 1", url="https://test.com/new1.torrent"),  # New torrent
            Torrent(name="New Torrent 2", url="https://test.com/new2.torrent"),  # New torrent
        ]

        new_torrents = db.torrent.check_new(test_torrents)
        assert len(new_torrents) == 2
        assert new_torrents[0].name == "New Torrent 1"
        assert new_torrents[1].name == "New Torrent 2"

        # Test with existing but not downloaded torrent (should be considered "new")
        test_torrents_2 = [
            Torrent(name="Not Downloaded", url="https://test.com/not_downloaded.torrent"),  # Exists but not downloaded
            Torrent(name="Another New", url="https://test.com/another_new.torrent"),  # New torrent
        ]

        new_torrents_2 = db.torrent.check_new(test_torrents_2)
        assert len(new_torrents_2) == 2  # Both should be considered "new"


def test_torrent_database_delete():
    with Database(TEST_ENGINE) as db:
        # Verify torrents exist before deletion
        torrent1 = db.torrent.search_by_url("https://test.com/delete1.torrent")
        torrent2 = db.torrent.search_by_duid("uid_002")
        assert torrent1 is not None
        assert torrent2 is not None

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
    # Add a new torrent for integration test
    test_data = Torrent(
        name="[Sub Group]integration test [720p].mkv",
        url="https://test.com/integration_test.mkv",
    )
    with Database(TEST_ENGINE) as db:
        # insert
        db.torrent.add(test_data)
        torrent = db.torrent.search_by_url(test_data.url)
        assert torrent is not None
        assert torrent.name == test_data.name
        assert torrent.url == test_data.url
        assert torrent.downloaded is False

        # update
        updated_data = Torrent(name=test_data.name, url=test_data.url, downloaded=True)
        db.torrent.add(updated_data)
        torrent = db.torrent.search_by_url(test_data.url)
        assert torrent is not None
        assert torrent.name == test_data.name
        assert torrent.url == test_data.url
        assert torrent.downloaded is True
