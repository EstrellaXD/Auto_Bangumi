from module.database.combine import Database
from models import RSSItem
from sqlmodel import create_engine
from sqlmodel.pool import StaticPool

# 模块级别共享的 engine
TEST_ENGINE = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)

# 初始化表结构
with Database(TEST_ENGINE) as db:
    db.create_table()


def test_rss_database_add():
    # 准备所有测试数据
    test_rss_list = [
        RSSItem(
            name="Test RSS Feed",
            url="https://test.com/test1.xml",
            aggregate=True,
            parser="mikan",
            enabled=True,
        ),
        RSSItem(
            name="Search RSS Feed",
            url="https://test.com/search_test.xml",
            aggregate=True,
            parser="mikan",
            enabled=True,
        ),
        RSSItem(
            name="Enable Test RSS",
            url="https://test.com/enable_test.xml",
            aggregate=True,
            parser="mikan",
            enabled=True,
        ),
        RSSItem(
            name="Original RSS Feed",
            url="https://test.com/update_test.xml",
            aggregate=True,
            parser="mikan",
            enabled=True,
        ),
        RSSItem(
            name="Delete RSS Feed",
            url="https://test.com/delete_test.xml",
            aggregate=True,
            parser="mikan",
            enabled=True,
        ),
        RSSItem(
            name="Duplicate RSS",
            url="https://test.com/duplicate_test.xml",
            aggregate=True,
            parser="mikan",
            enabled=True,
        ),
        RSSItem(
            name="RSS Feed 1",
            url="https://test.com/batch1.xml",
            aggregate=False,
            parser="nyaa",
            enabled=True,
        ),
        RSSItem(
            name="RSS Feed 2",
            url="https://test.com/batch2.xml",
            aggregate=True,
            parser="mikan",
            enabled=False,
        ),
    ]
    
    with Database(TEST_ENGINE) as db:
        # 批量插入所有测试数据
        for rss_item in test_rss_list:
            result = db.rss.add(rss_item)
            assert result is True
        
        # 验证插入成功
        all_rss = db.rss.search_all()
        assert len(all_rss) == len(test_rss_list)
        
        # Test search by ID
        rss_item = db.rss.search_id(1)
        assert rss_item is not None
        assert rss_item.name == "Test RSS Feed"


def test_rss_database_search():
    with Database(TEST_ENGINE) as db:
        # Test search_all
        all_rss = db.rss.search_all()
        assert len(all_rss) >= 8  # Should have at least 8 RSS items from add test
        
        # Test search_url
        rss_by_url = db.rss.search_url("https://test.com/search_test.xml")
        assert rss_by_url is not None
        assert rss_by_url.name == "Search RSS Feed"
        
        # Test search_url non-existent
        nonexistent = db.rss.search_url("https://nonexistent.com")
        assert nonexistent is None


def test_rss_database_enable_disable():
    with Database(TEST_ENGINE) as db:
        # Test search_active (should find enabled RSS items)
        active_rss = db.rss.search_active()
        initial_active_count = len(active_rss)
        assert initial_active_count > 0
        
        # Find "Enable Test RSS" (should be id=3)
        enable_test_rss = db.rss.search_url("https://test.com/enable_test.xml")
        assert enable_test_rss is not None
        assert enable_test_rss.enabled is True
        
        # Test disable
        disable_result = db.rss.disable(enable_test_rss.id)
        assert disable_result is True
        disabled_rss = db.rss.search_id(enable_test_rss.id)
        assert disabled_rss.enabled is False
        
        # Test search_active after disable
        active_after_disable = db.rss.search_active()
        assert len(active_after_disable) == initial_active_count - 1
        
        # Test enable
        enable_result = db.rss.enable(enable_test_rss.id)
        assert enable_result is True
        enabled_rss = db.rss.search_id(enable_test_rss.id)
        assert enabled_rss.enabled is True


def test_rss_database_update():
    with Database(TEST_ENGINE) as db:
        # Find "Original RSS Feed" (should be id=4)
        original_rss = db.rss.search_url("https://test.com/update_test.xml")
        assert original_rss is not None
        assert original_rss.name == "Original RSS Feed"
        
        # Test update
        original_rss.name = "Updated RSS Feed"
        update_result = db.rss.update(original_rss)
        assert update_result is True
        
        updated_rss = db.rss.search_id(original_rss.id)
        assert updated_rss.name == "Updated RSS Feed"


def test_rss_database_delete():
    with Database(TEST_ENGINE) as db:
        # Find "Delete RSS Feed" (should be id=5)
        delete_rss = db.rss.search_url("https://test.com/delete_test.xml")
        assert delete_rss is not None
        assert delete_rss.name == "Delete RSS Feed"
        
        # Test delete
        delete_result = db.rss.delete(delete_rss.id)
        assert delete_result is True
        deleted_rss = db.rss.search_id(delete_rss.id)
        assert deleted_rss is None
        
        # Test delete non-existent ID
        delete_nonexistent = db.rss.delete(999)
        assert delete_nonexistent is False


def test_rss_database_duplicate():
    with Database(TEST_ENGINE) as db:
        # Test add duplicate URL (should already exist from add test)
        duplicate_rss = RSSItem(
            name="Another Duplicate RSS",
            url="https://test.com/duplicate_test.xml",  # Same URL as existing
            aggregate=False,
            parser="nyaa",
            enabled=False,
        )
        result = db.rss.add(duplicate_rss)
        assert result is False  # Should not add duplicate URL
        
        # Verify the original RSS item still exists
        original_rss = db.rss.search_url("https://test.com/duplicate_test.xml")
        assert original_rss is not None
        assert original_rss.name == "Duplicate RSS"  # Should keep original name


def test_rss_database_add_all():
    # Test add_all with new RSS items (using unique URLs)
    test_rss_list = [
        RSSItem(
            name="Add All RSS 1",
            url="https://test.com/add_all_1.xml",
            aggregate=False,
            parser="nyaa",
            enabled=True,
        ),
        RSSItem(
            name="Add All RSS 2",
            url="https://test.com/add_all_2.xml",
            aggregate=True,
            parser="mikan",
            enabled=False,
        ),
    ]
    
    with Database(TEST_ENGINE) as db:
        # Get initial count
        initial_count = len(db.rss.search_all())
        
        # Test add_all
        db.rss.add_all(test_rss_list)
        
        all_rss = db.rss.search_all()
        assert len(all_rss) == initial_count + 2
        
        # Verify the new items were added
        new_rss1 = db.rss.search_url("https://test.com/add_all_1.xml")
        new_rss2 = db.rss.search_url("https://test.com/add_all_2.xml")
        assert new_rss1 is not None
        assert new_rss2 is not None
        assert new_rss1.enabled is True
        assert new_rss2.enabled is False


def test_rss_database_integration():
    """Basic integration test for RSS database operations"""
    # Add a new RSS item for integration test
    test_data = RSSItem(
        name="Test RSS Feed Integration",
        url="https://test.com/integration_test.xml",
        aggregate=True,
        parser="mikan",
        enabled=True,
    )
    
    with Database(TEST_ENGINE) as db:
        # Test add
        result = db.rss.add(test_data)
        assert result is True
        
        # Test search (find the newly added item)
        rss_item = db.rss.search_url(test_data.url)
        assert rss_item is not None
        assert rss_item.url == test_data.url
        assert rss_item.name == test_data.name
        
        # Test enable/disable
        db.rss.disable(rss_item.id)
        disabled_rss = db.rss.search_id(rss_item.id)
        assert disabled_rss.enabled is False
        
        db.rss.enable(rss_item.id)
        enabled_rss = db.rss.search_id(rss_item.id)
        assert enabled_rss.enabled is True
        
        # Test delete
        db.rss.delete(rss_item.id)
        deleted_rss = db.rss.search_id(rss_item.id)
        assert deleted_rss is None
