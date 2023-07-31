from sqlmodel import create_engine, SQLModel
from sqlmodel.pool import StaticPool

from module.database import BangumiDatabase
from module.models import Bangumi


def test_bangumi_database():
    # sqlite mock engine
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    test_data = Bangumi(
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
        filter="720p,\\d+-\\d+",
        rss_link="test",
        poster_link="/test/test.jpg",
        added=False,
        rule_name=None,
        save_path=None,
        deleted=False,
    )
    with BangumiDatabase(engine) as database:
        # insert
        database.insert_one(test_data)
        assert database.search_id(1) == test_data

        # update
        test_data.official_title = "test2"
        database.update_one(test_data)
        assert database.search_id(1) == test_data

        # search poster
        assert database.match_poster("test2 (2021)") == "/test/test.jpg"

        # delete
        database.delete_one(1)
        assert database.search_id(1) is None
