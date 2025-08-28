from module.database.combine import Database
from module.models import Bangumi
from sqlmodel import create_engine
from sqlmodel.pool import StaticPool


def create_test_engine():
    """Create a new in-memory SQLite engine for each test"""
    return create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )


def test_bangumi_database_add():
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
        exclude_filter="720p,\\d+-\\d+",
        rss_link="test",
        poster_link="/test/test.jpg",
        added=False,
        rule_name=None,
        deleted=False,
    )
    with Database(create_test_engine()) as db:
        db.create_table()
        
        # Test add
        result = db.bangumi.add(test_data)
        assert result is True
        
        # Test search by ID
        bangumi = db.bangumi.search_id(1)
        assert bangumi == test_data
        assert bangumi.official_title == "无职转生，到了异世界就拿出真本事"


def test_bangumi_database_update():
    test_data = Bangumi(
        official_title="无职转生，到了异世界就拿出真本事",
        year="2021",
        title_raw="Mushoku Tensei",
        season=1,
        rss_link="test",
        poster_link="/test/test.jpg",
    )
    
    with Database(create_test_engine()) as db:
        db.create_table()
        db.bangumi.add(test_data)
        
        # Get the bangumi from database to ensure it's attached to session
        bangumi = db.bangumi.search_id(1)
        bangumi.official_title = "无职转生，到了异世界就拿出真本事II"
        
        # Test update
        result = db.bangumi.update(bangumi)
        assert result is True
        
        updated_bangumi = db.bangumi.search_id(1)
        assert updated_bangumi.official_title == "无职转生，到了异世界就拿出真本事II"


def test_bangumi_database_search():
    test_data = Bangumi(
        official_title="无职转生，到了异世界就拿出真本事II",
        year="2021",
        title_raw="Mushoku Tensei",
        season=1,
        rss_link="test",
        poster_link="/test/test.jpg",
    )
    
    with Database(create_test_engine()) as db:
        db.create_table()
        db.bangumi.add(test_data)
        
        # Test search_official_title
        bangumi_by_title = db.bangumi.search_official_title("无职转生，到了异世界就拿出真本事II")
        assert bangumi_by_title is not None
        assert bangumi_by_title.poster_link == "/test/test.jpg"
        
        # Test search_all
        all_bangumi = db.bangumi.search_all()
        assert len(all_bangumi) == 1
        assert all_bangumi[0].official_title == "无职转生，到了异世界就拿出真本事II"
        
        # Test search by title, season, rss_link
        bangumi_by_params = db.bangumi.search("无职转生，到了异世界就拿出真本事II", 1, "test")
        assert bangumi_by_params is not None
        assert bangumi_by_params.official_title == "无职转生，到了异世界就拿出真本事II"


def test_bangumi_database_delete():
    test_data = Bangumi(
        official_title="Test Bangumi",
        title_raw="Test Raw",
        season=1,
        rss_link="test",
    )
    
    with Database(create_test_engine()) as db:
        db.create_table()
        db.bangumi.add(test_data)
        
        # Verify it exists
        bangumi = db.bangumi.search_id(1)
        assert bangumi is not None
        
        # Test delete
        db.bangumi.delete_one(1)
        deleted_bangumi = db.bangumi.search_id(1)
        assert deleted_bangumi is None


def test_bangumi_database_title_raw_merge():
    test_data = Bangumi(
        official_title="Test Bangumi",
        title_raw="Original Title",
        season=1,
        rss_link="test_merge",
        group_name="Group1",
    )
    
    with Database(create_test_engine()) as db:
        db.create_table()
        
        # Add first bangumi
        result1 = db.bangumi.add(test_data)
        assert result1 is True
        
        # Add same bangumi with different title_raw
        duplicate_data = Bangumi(
            official_title="Test Bangumi",
            title_raw="Another Title",
            season=1,
            rss_link="test_merge",
            group_name="Group2",
        )
        
        result2 = db.bangumi.add(duplicate_data)
        assert result2 is True  # Will merge the data, so returns True
        
        # Check that title_raw and group_name were merged
        bangumi = db.bangumi.search_id(1)
        assert bangumi is not None
        assert "Original Title" in bangumi.title_raw
        assert "Another Title" in bangumi.title_raw
        assert "Group1" in bangumi.group_name
        assert "Group2" in bangumi.group_name
        
        # Test adding exact same title_raw - should return False
        duplicate_exact = Bangumi(
            official_title="Test Bangumi",
            title_raw="Original Title",  # Same as first one
            season=1,
            rss_link="test_merge",
            group_name="Group3",
        )
        result3 = db.bangumi.add(duplicate_exact)
        assert result3 is False  # Should not add exact duplicate title_raw


def test_bangumi_database_not_complete():
    complete_bangumi = Bangumi(
        official_title="Complete Bangumi",
        title_raw="Complete",
        season=1,
        rss_link="test1",
        eps_collect=True,
        deleted=False,
    )
    
    incomplete_bangumi = Bangumi(
        official_title="Incomplete Bangumi",
        title_raw="Incomplete",
        season=1,
        rss_link="test2",
        eps_collect=False,
        deleted=False,
    )
    
    deleted_bangumi = Bangumi(
        official_title="Deleted Bangumi",
        title_raw="Deleted",
        season=1,
        rss_link="test3",
        eps_collect=False,
        deleted=True,
    )
    
    with Database(create_test_engine()) as db:
        db.create_table()
        db.bangumi.add(complete_bangumi)
        db.bangumi.add(incomplete_bangumi)
        db.bangumi.add(deleted_bangumi)
        
        # Test not_complete
        not_complete = db.bangumi.not_complete()
        assert len(not_complete) == 1
        assert not_complete[0].official_title == "Incomplete Bangumi"


def test_bangumi_database_update_all():
    bangumi_list = [
        Bangumi(
            official_title="Bangumi 1",
            title_raw="Raw 1",
            season=1,
            rss_link="test1",
            poster_link="/old/poster1.jpg",
        ),
        Bangumi(
            official_title="Bangumi 2", 
            title_raw="Raw 2",
            season=1,
            rss_link="test2",
            poster_link="/old/poster2.jpg",
        ),
    ]
    
    with Database(create_test_engine()) as db:
        db.create_table()
        
        # Add initial bangumi
        for bangumi in bangumi_list:
            db.bangumi.add(bangumi)
        
        # Update poster links
        updated_bangumi_list = db.bangumi.search_all()
        for bangumi in updated_bangumi_list:
            bangumi.poster_link = f"/new/poster{bangumi.id}.jpg"
        
        # Test update_all
        db.bangumi.update_all(updated_bangumi_list)
        
        # Verify updates
        all_bangumi = db.bangumi.search_all()
        for bangumi in all_bangumi:
            assert "/new/poster" in bangumi.poster_link


def test_bangumi_database_delete_all():
    bangumi_list = [
        Bangumi(official_title="Test 1", title_raw="Raw 1", season=1, rss_link="test1"),
        Bangumi(official_title="Test 2", title_raw="Raw 2", season=1, rss_link="test2"),
        Bangumi(official_title="Test 3", title_raw="Raw 3", season=1, rss_link="test3"),
    ]
    
    with Database(create_test_engine()) as db:
        db.create_table()
        
        # Add bangumi
        for bangumi in bangumi_list:
            db.bangumi.add(bangumi)
        
        # Verify they exist
        all_bangumi = db.bangumi.search_all()
        assert len(all_bangumi) == 3
        
        # Test delete_all
        db.bangumi.delete_all()
        
        # Verify all deleted
        all_bangumi_after = db.bangumi.search_all()
        assert len(all_bangumi_after) == 0


def test_bangumi_database_integration():
    """Integration test that includes RawParser and find_bangumi_by_name functionality"""
    from module.parser import RawParser
    
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
        exclude_filter="720p,\\d+-\\d+",
        rss_link="test",
        poster_link="/test/test.jpg",
        added=False,
        rule_name=None,
        deleted=False,
    )
    with Database(create_test_engine()) as db:
        db.create_table()
        # insert
        db.bangumi.add(test_data)
        assert db.bangumi.search_id(1) == test_data

        # update
        bangumi = db.bangumi.search_id(1)
        bangumi.official_title = "无职转生，到了异世界就拿出真本事II"
        db.bangumi.update(bangumi)
        updated_bangumi = db.bangumi.search_id(1)
        assert updated_bangumi.official_title == "无职转生，到了异世界就拿出真本事II"

        # search poster
        data = db.bangumi.search_official_title("无职转生，到了异世界就拿出真本事II")
        assert data.poster_link == "/test/test.jpg"

        # match torrent using RawParser
        title = (
            RawParser()
            .parser(
                "[Lilith-Raws] 无职转生，到了异世界就拿出真本事 / Mushoku Tensei - 11 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4]"
            )
            .title_raw
        )
        result = db.find_bangumi_by_name(
            title,
            "test",
            True,
        )
        assert result.official_title == "无职转生，到了异世界就拿出真本事II"

        # delete
        db.bangumi.delete_one(1)
        assert db.bangumi.search_id(1) is None