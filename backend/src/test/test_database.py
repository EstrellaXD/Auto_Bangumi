from module.database import BangumiDatabase
from module.models import BangumiData


def test_database():
    TEST_PATH = "test/test.db"
    test_data = BangumiData(
        id=1,
        official_title="test",
        year="2021",
        title_raw="test",
        season=1,
        season_raw="第一季",
        group_name="test",
        dpi="720p",
        source="test",
        subtitle="test",
        eps_collect=False,
        offset=0,
        filter=["720p", "\\d+-\\d+"],
        rss_link=["test"],
        poster_link="/test/test.jpg",
        added=False,
        rule_name=None,
        save_path=None,
        deleted=False,
    )
    with BangumiDatabase(database=TEST_PATH) as database:
        # create table
        database.update_table()
    with BangumiDatabase(database=TEST_PATH) as database:
        # insert
        database.insert_one(test_data)
        assert database.search_id(1) == test_data

        # update
        test_data.official_title = "test2"
        database.update_one(test_data)
        assert database.search_id(1) == test_data

        # search poster
        assert database.match_poster("test") == "/test/test.jpg"

        # delete
        database.delete_one(1)
        assert database.search_id(1) is None
