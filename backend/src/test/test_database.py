import pytest
from sqlmodel import Session, SQLModel, create_engine

from module.database.bangumi import BangumiDatabase
from module.database.rss import RSSDatabase
from module.database.torrent import TorrentDatabase
from module.models import Bangumi, RSSItem, Torrent

# sqlite sync engine for testing
engine = create_engine("sqlite://", echo=False)


@pytest.fixture
def db_session():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


def test_bangumi_database(db_session):
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
        filter="720p,\\d+-\\d+",
        rss_link="test",
        poster_link="/test/test.jpg",
        added=False,
        rule_name=None,
        save_path="downloads/无职转生，到了异世界就拿出真本事/Season 1",
        deleted=False,
    )
    db = BangumiDatabase(db_session)

    # insert
    db.add(test_data)
    result = db.search_id(1)
    assert result.official_title == test_data.official_title

    # update
    test_data.official_title = "无职转生，到了异世界就拿出真本事II"
    db.update(test_data)
    result = db.search_id(1)
    assert result.official_title == test_data.official_title

    # search poster
    poster = db.match_poster("无职转生，到了异世界就拿出真本事II (2021)")
    assert poster == "/test/test.jpg"

    # match torrent
    result = db.match_torrent(
        "[Lilith-Raws] 无职转生，到了异世界就拿出真本事 / Mushoku Tensei - 11 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4]"
    )
    assert result.official_title == "无职转生，到了异世界就拿出真本事II"

    # delete
    db.delete_one(1)
    result = db.search_id(1)
    assert result is None


def test_torrent_database(db_session):
    test_data = Torrent(
        name="[Sub Group]test S02 01 [720p].mkv",
        url="https://test.com/test.mkv",
    )
    db = TorrentDatabase(db_session)

    # insert
    db.add(test_data)
    result = db.search(1)
    assert result.name == test_data.name

    # update
    test_data.downloaded = True
    db.update(test_data)
    result = db.search(1)
    assert result.downloaded == True


def test_rss_database(db_session):
    rss_url = "https://test.com/test.xml"
    db = RSSDatabase(db_session)

    db.add(RSSItem(url=rss_url, name="Test RSS"))
    result = db.search_id(1)
    assert result.url == rss_url
