from sqlmodel import create_engine, SQLModel
from sqlmodel.pool import StaticPool

from module.database.combine import Database
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
    with Database(engine) as db:
        # insert
        db.bangumi.insert_one(test_data)
        assert db.bangumi.search_id(1) == test_data

        # update
        test_data.official_title = "test2"
        db.bangumi.update_one(test_data)
        assert db.bangumi.search_id(1) == test_data

        # search poster
        assert db.bangumi.match_poster("test2 (2021)") == "/test/test.jpg"

        # delete
        db.bangumi.delete_one(1)
        assert db.bangumi.search_id(1) is None
