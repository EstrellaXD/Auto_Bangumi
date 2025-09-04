from module.database.combine import Database
from module.models import Bangumi
from sqlmodel import create_engine
from sqlmodel.pool import StaticPool

# 模块级别共享的 engine
TEST_ENGINE = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

# 初始化表结构
with Database(TEST_ENGINE) as db:
    db.create_table()


def test_bangumi_database_add():
    # 准备所有测试数据
    test_bangumi_list = [
        Bangumi(
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
            rss_link="test1",
            poster_link="/test/test1.jpg",
            added=False,
            rule_name=None,
            deleted=False,
        ),
        Bangumi(
            official_title="Test Bangumi",
            title_raw="Test Raw",
            season=1,
            rss_link="test2",
            poster_link="/test/test2.jpg",
        ),
        Bangumi(
            official_title="Complete Bangumi",
            title_raw="Complete",
            season=1,
            rss_link="test3",
            eps_collect=True,
            deleted=False,
        ),
        Bangumi(
            official_title="Incomplete Bangumi",
            title_raw="Incomplete",
            season=1,
            rss_link="test4",
            eps_collect=False,
            deleted=False,
        ),
        Bangumi(
            official_title="Deleted Bangumi",
            title_raw="Deleted",
            season=1,
            rss_link="test5",
            eps_collect=False,
            deleted=True,
        ),
        Bangumi(
            official_title="Merge Test Bangumi",
            title_raw="Original Title",
            season=1,
            rss_link="test_merge",
            group_name="Group1",
        ),
        Bangumi(
            official_title="Bangumi 1",
            title_raw="Raw 1",
            season=1,
            rss_link="test6",
            poster_link="/old/poster1.jpg",
        ),
        Bangumi(
            official_title="Bangumi 2",
            title_raw="Raw 2",
            season=1,
            rss_link="test7",
            poster_link="/old/poster2.jpg",
        ),
    ]

    with Database(TEST_ENGINE) as db:
        # 批量插入所有测试数据
        for bangumi in test_bangumi_list:
            result = db.bangumi.add(bangumi)
            assert result is True

        # 验证插入成功
        all_bangumi = db.bangumi.search_all()
        assert len(all_bangumi) == len(test_bangumi_list)

        # Test search by ID
        bangumi = db.bangumi.search_id(1)
        assert bangumi.official_title == "无职转生，到了异世界就拿出真本事"


def test_bangumi_database_update():
    with Database(TEST_ENGINE) as db:
        # Get the bangumi from database to ensure it's attached to session
        bangumi = db.bangumi.search_id(1)
        assert bangumi is not None

    with Database(TEST_ENGINE) as db:
        bangumi.official_title = "无职转生，到了异世界就拿出真本事II"

        # Test update
        result = db.bangumi.update(bangumi)
        assert result is True

        updated_bangumi = db.bangumi.search_id(1)
        assert updated_bangumi.official_title == "无职转生，到了异世界就拿出真本事II"


def test_bangumi_database_search():
    with Database(TEST_ENGINE) as db:
        # Test search_official_title (using updated title from previous test)
        bangumi_by_title = db.bangumi.search_official_title("无职转生，到了异世界就拿出真本事II")
        assert bangumi_by_title is not None
        assert bangumi_by_title.poster_link == "/test/test1.jpg"

        # Test search_all
        all_bangumi = db.bangumi.search_all()
        assert len(all_bangumi) >= 8  # Should have at least 8 bangumi from add test

        # Test search by title, season, rss_link
        bangumi_by_params = db.bangumi.search("无职转生，到了异世界就拿出真本事II", 1, "test1")
        assert bangumi_by_params is not None
        assert bangumi_by_params.official_title == "无职转生，到了异世界就拿出真本事II"


def test_bangumi_database_delete():
    with Database(TEST_ENGINE) as db:
        # Verify Test Bangumi exists (should be id=2)
        bangumi = db.bangumi.search_id(2)
        assert bangumi is not None
        assert bangumi.official_title == "Test Bangumi"

        # Test delete
        db.bangumi.delete_one(2)
        deleted_bangumi = db.bangumi.search_id(2)
        assert deleted_bangumi is None


def test_bangumi_database_title_raw_merge():
    with Database(TEST_ENGINE) as db:
        # Find the Merge Test Bangumi (should be id=6)
        merge_bangumi = db.bangumi.search_official_title("Merge Test Bangumi")
        assert merge_bangumi is not None
        assert "Original Title" in merge_bangumi.title_raw
        assert "Group1" in merge_bangumi.group_name

        # Add same bangumi with different title_raw
        duplicate_data = Bangumi(
            official_title="Merge Test Bangumi",
            title_raw="Another Title",
            season=1,
            rss_link="test_merge",
            group_name="Group2",
        )

        result2 = db.bangumi.add(duplicate_data)
        assert result2 is True  # Will merge the data, so returns True

        # Check that title_raw and group_name were merged
        updated_bangumi = db.bangumi.search_official_title("Merge Test Bangumi")
        assert updated_bangumi is not None
        assert "Original Title" in updated_bangumi.title_raw
        assert "Another Title" in updated_bangumi.title_raw
        assert "Group1" in updated_bangumi.group_name
        assert "Group2" in updated_bangumi.group_name

        # Test adding exact same title_raw - should return False
        duplicate_exact = Bangumi(
            official_title="Merge Test Bangumi",
            title_raw="Original Title",  # Same as first one
            season=1,
            rss_link="test_merge",
            group_name="Group3",
        )
        result3 = db.bangumi.add(duplicate_exact)
        assert result3 is False  # Should not add exact duplicate title_raw


def test_bangumi_database_not_complete():
    with Database(TEST_ENGINE) as db:
        # Test not_complete (should find bangumi that are eps_collect=False and deleted=False)
        not_complete = db.bangumi.not_complete()
        # Should find "Incomplete Bangumi" and possibly others
        incomplete_titles = [b.official_title for b in not_complete]
        assert "Incomplete Bangumi" in incomplete_titles
        # Should not include "Complete Bangumi" (eps_collect=True) or "Deleted Bangumi" (deleted=True)
        assert "Complete Bangumi" not in incomplete_titles
        assert "Deleted Bangumi" not in incomplete_titles


def test_bangumi_database_update_all():
    with Database(TEST_ENGINE) as db:
        # Get "Bangumi 1" and "Bangumi 2" from existing data
        bangumi1 = db.bangumi.search_official_title("Bangumi 1")
        bangumi2 = db.bangumi.search_official_title("Bangumi 2")
        assert bangumi1 is not None
        assert bangumi2 is not None

        # Update their poster links
        bangumi1.poster_link = f"/new/poster{bangumi1.id}.jpg"
        bangumi2.poster_link = f"/new/poster{bangumi2.id}.jpg"

        # Test update_all
        db.bangumi.update_all([bangumi1, bangumi2])

        # Verify updates
        updated_bangumi1 = db.bangumi.search_official_title("Bangumi 1")
        updated_bangumi2 = db.bangumi.search_official_title("Bangumi 2")
        assert "/new/poster" in updated_bangumi1.poster_link
        assert "/new/poster" in updated_bangumi2.poster_link


def test_bangumi_database_delete_all():
    with Database(TEST_ENGINE) as db:
        # Verify we have bangumi before deletion
        all_bangumi_before = db.bangumi.search_all()
        assert len(all_bangumi_before) > 0

        # Test delete_all
        db.bangumi.delete_all()

        # Verify all deleted
        all_bangumi_after = db.bangumi.search_all()
        assert len(all_bangumi_after) == 0


def test_bangumi_database_integration():
    """Integration test that includes RawParser and find_bangumi_by_name functionality"""
    from module.parser import RawParser

    # Need to re-add data since previous test deleted everything
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
    with Database(TEST_ENGINE) as db:
        # insert
        db.bangumi.add(test_data)
        bangumi = db.bangumi.search_id(1)
        assert bangumi.official_title == test_data.official_title

        # update
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
