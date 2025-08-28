from module.database.combine import Database
from module.models import RSSItem
from sqlmodel import create_engine
from sqlmodel.pool import StaticPool


def create_test_engine():
    """Create a new in-memory SQLite engine for each test"""
    return create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )


def test_rss_database_add():
    test_data = RSSItem(
        name="Test RSS Feed",
        url="https://test.com/test.xml",
        aggregate=True,
        parser="mikan",
        enabled=True,
    )
    
    with Database(create_test_engine()) as db:
        db.create_table()
        
        # Test add
        result = db.rss.add(test_data)
        assert result is True
        
        # Test search by ID
        rss_item = db.rss.search_id(1)
        assert rss_item is not None
        assert rss_item.url == test_data.url
        assert rss_item.name == test_data.name


def test_rss_database_search():
    test_data = RSSItem(
        name="Test RSS Feed",
        url="https://test.com/search_test.xml",
        aggregate=True,
        parser="mikan",
        enabled=True,
    )
    
    with Database(create_test_engine()) as db:
        db.create_table()
        db.rss.add(test_data)
        
        # Test search_all
        all_rss = db.rss.search_all()
        assert len(all_rss) == 1
        assert all_rss[0].url == test_data.url
        
        # Test search_url
        rss_by_url = db.rss.search_url(test_data.url)
        assert rss_by_url is not None
        assert rss_by_url.name == test_data.name
        
        # Test search_url non-existent
        nonexistent = db.rss.search_url("https://nonexistent.com")
        assert nonexistent is None


def test_rss_database_enable_disable():
    test_data = RSSItem(
        name="Test RSS Feed",
        url="https://test.com/enable_test.xml",
        aggregate=True,
        parser="mikan",
        enabled=True,
    )
    
    with Database(create_test_engine()) as db:
        db.create_table()
        db.rss.add(test_data)
        
        # Test search_active
        active_rss = db.rss.search_active()
        assert len(active_rss) == 1
        
        # Test disable
        disable_result = db.rss.disable(1)
        assert disable_result is True
        disabled_rss = db.rss.search_id(1)
        assert disabled_rss.enabled is False
        
        # Test search_active after disable
        active_after_disable = db.rss.search_active()
        assert len(active_after_disable) == 0
        
        # Test enable
        enable_result = db.rss.enable(1)
        assert enable_result is True
        enabled_rss = db.rss.search_id(1)
        assert enabled_rss.enabled is True


def test_rss_database_update():
    test_data = RSSItem(
        name="Original RSS Feed",
        url="https://test.com/update_test.xml",
        aggregate=True,
        parser="mikan",
        enabled=True,
    )
    
    with Database(create_test_engine()) as db:
        db.create_table()
        db.rss.add(test_data)
        
        # Test update
        rss_item = db.rss.search_id(1)
        rss_item.name = "Updated RSS Feed"
        update_result = db.rss.update(rss_item)
        assert update_result is True
        
        updated_rss = db.rss.search_id(1)
        assert updated_rss.name == "Updated RSS Feed"


def test_rss_database_delete():
    test_data = RSSItem(
        name="Test RSS Feed",
        url="https://test.com/delete_test.xml",
        aggregate=True,
        parser="mikan",
        enabled=True,
    )
    
    with Database(create_test_engine()) as db:
        db.create_table()
        db.rss.add(test_data)
        
        # Test delete
        delete_result = db.rss.delete(1)
        assert delete_result is True
        deleted_rss = db.rss.search_id(1)
        assert deleted_rss is None
        
        # Test delete non-existent ID
        delete_nonexistent = db.rss.delete(999)
        assert delete_nonexistent is False


def test_rss_database_duplicate():
    test_data = RSSItem(
        name="Original RSS",
        url="https://test.com/duplicate_test.xml",
        aggregate=True,
        parser="mikan",
        enabled=True,
    )
    
    with Database(create_test_engine()) as db:
        db.create_table()
        
        # First add
        result1 = db.rss.add(test_data)
        assert result1 is True
        
        # Test add duplicate URL
        duplicate_rss = RSSItem(
            name="Duplicate RSS",
            url="https://test.com/duplicate_test.xml",
            aggregate=False,
            parser="nyaa",
            enabled=False,
        )
        result2 = db.rss.add(duplicate_rss)
        assert result2 is False
        
        # Should still have only one item
        all_rss = db.rss.search_all()
        assert len(all_rss) == 1


def test_rss_database_add_all():
    test_rss_list = [
        RSSItem(
            name="RSS Feed 1",
            url="https://test.com/test1.xml",
            aggregate=False,
            parser="nyaa",
            enabled=True,
        ),
        RSSItem(
            name="RSS Feed 2",
            url="https://test.com/test2.xml",
            aggregate=True,
            parser="mikan",
            enabled=False,
        ),
    ]
    
    with Database(create_test_engine()) as db:
        db.create_table()
        
        # Test add_all
        db.rss.add_all(test_rss_list)
        
        all_rss = db.rss.search_all()
        assert len(all_rss) == 2
        
        active_rss = db.rss.search_active()
        assert len(active_rss) == 1


def test_rss_database_integration():
    """Basic integration test for RSS database operations"""
    test_data = RSSItem(
        name="Test RSS Feed Integration",
        url="https://test.com/integration_test.xml",
        aggregate=True,
        parser="mikan",
        enabled=True,
    )
    
    with Database(create_test_engine()) as db:
        db.create_table()
        
        # Test add
        result = db.rss.add(test_data)
        assert result is True
        
        # Test search
        rss_item = db.rss.search_id(1)
        assert rss_item is not None
        assert rss_item.url == test_data.url
        assert rss_item.name == test_data.name
        
        # Test enable/disable
        db.rss.disable(1)
        disabled_rss = db.rss.search_id(1)
        assert disabled_rss.enabled is False
        
        db.rss.enable(1)
        enabled_rss = db.rss.search_id(1)
        assert enabled_rss.enabled is True
        
        # Test delete
        db.rss.delete(1)
        deleted_rss = db.rss.search_id(1)
        assert deleted_rss is None