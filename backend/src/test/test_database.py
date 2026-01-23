import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from module.database.bangumi import BangumiDatabase
from module.database.rss import RSSDatabase
from module.database.torrent import TorrentDatabase
from module.models import Bangumi, RSSItem, Torrent

# sqlite async mock engine
engine = create_async_engine(
    "sqlite+aiosqlite://",
    echo=False,
)
async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with async_session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest.mark.asyncio
async def test_bangumi_database(db_session):
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
    await db.add(test_data)
    result = await db.search_id(1)
    assert result.official_title == test_data.official_title

    # update
    test_data.official_title = "无职转生，到了异世界就拿出真本事II"
    await db.update(test_data)
    result = await db.search_id(1)
    assert result.official_title == test_data.official_title

    # search poster
    poster = await db.match_poster("无职转生，到了异世界就拿出真本事II (2021)")
    assert poster == "/test/test.jpg"

    # match torrent
    result = await db.match_torrent(
        "[Lilith-Raws] 无职转生，到了异世界就拿出真本事 / Mushoku Tensei - 11 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4]"
    )
    assert result.official_title == "无职转生，到了异世界就拿出真本事II"

    # delete
    await db.delete_one(1)
    result = await db.search_id(1)
    assert result is None


@pytest.mark.asyncio
async def test_torrent_database(db_session):
    test_data = Torrent(
        name="[Sub Group]test S02 01 [720p].mkv",
        url="https://test.com/test.mkv",
    )
    db = TorrentDatabase(db_session)

    # insert
    await db.add(test_data)
    result = await db.search(1)
    assert result.name == test_data.name

    # update
    test_data.downloaded = True
    await db.update(test_data)
    result = await db.search(1)
    assert result.downloaded == True


@pytest.mark.asyncio
async def test_rss_database(db_session):
    rss_url = "https://test.com/test.xml"
    db = RSSDatabase(db_session)

    await db.add(RSSItem(url=rss_url, name="Test RSS"))
    result = await db.search_id(1)
    assert result.url == rss_url
