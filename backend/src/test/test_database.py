from sqlmodel import create_engine, SQLModel
from sqlmodel.pool import StaticPool

from module.database.combine import Database
from module.models import Bangumi, Torrent, RSSItem


# sqlite mock engine
engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


def test_bangumi_database():
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
        db.create_table()
        # insert
        db.bangumi.add(test_data)
        assert db.bangumi.search_id(1) == test_data

        # update
        test_data.official_title = "test2"
        db.bangumi.update(test_data)
        assert db.bangumi.search_id(1) == test_data

        # search poster
        assert db.bangumi.match_poster("test2 (2021)") == "/test/test.jpg"

        # match torrent
        result = db.bangumi.match_torrent("[Sub Group]test S02 01 [720p].mkv")
        assert result.official_title == "test2"

        # delete
        db.bangumi.delete_one(1)
        assert db.bangumi.search_id(1) is None


def test_torrent_database():
    test_data = Torrent(
        name="[Sub Group]test S02 01 [720p].mkv",
        url="https://test.com/test.mkv",
    )
    with Database(engine) as db:
        # insert
        db.torrent.add(test_data)
        assert db.torrent.search(1) == test_data

        # update
        test_data.downloaded = True
        db.torrent.update(test_data)
        assert db.torrent.search(1) == test_data


def test_rss_database():
    rss_url = "https://test.com/test.xml"

    with Database(engine) as db:
        db.rss.add(RSSItem(url=rss_url))
