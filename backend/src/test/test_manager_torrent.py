"""Tests for TorrentManager.delete_rule RSS cleanup (#1053).

删除番剧时应一并清理其独立订阅（aggregate=False）的孤儿 RSS 条目；
聚合订阅与仍被其他番剧引用的订阅不受影响。
"""

from module.database import Database
from module.manager import TorrentManager
from test.factories import make_bangumi, make_rss_item

SUB_URL = "https://mikanani.me/RSS/Bangumi?bangumiId=9&subgroupid=1"


async def _seed(db: Database, *, bangumi=(), rss=()):
    for b in bangumi:
        await db.bangumi.add(b)
    for r in rss:
        await db.rss.add(r)


class TestDeleteRuleRSSCleanup:
    async def test_delete_rule_removes_orphan_sub_rss(self, db_engine):
        async with Database(engine=db_engine) as db:
            await _seed(
                db,
                bangumi=[make_bangumi(id=1, rss_link=SUB_URL)],
                rss=[make_rss_item(url=SUB_URL, aggregate=False)],
            )
            manager = TorrentManager(db)

            resp = await manager.delete_rule(1, file=False)

            assert resp.status is True
            assert await db.rss.search_url(SUB_URL) is None

    async def test_delete_rule_keeps_aggregate_rss(self, db_engine):
        async with Database(engine=db_engine) as db:
            await _seed(
                db,
                bangumi=[make_bangumi(id=1, rss_link=SUB_URL)],
                rss=[make_rss_item(url=SUB_URL, aggregate=True)],
            )
            manager = TorrentManager(db)

            await manager.delete_rule(1, file=False)

            assert await db.rss.search_url(SUB_URL) is not None

    async def test_delete_rule_keeps_rss_referenced_by_other_bangumi(self, db_engine):
        async with Database(engine=db_engine) as db:
            await _seed(
                db,
                bangumi=[
                    make_bangumi(id=1, rss_link=SUB_URL),
                    make_bangumi(
                        id=2,
                        official_title="Other Anime",
                        title_raw="Other Anime Raw",
                        rss_link=f"https://example.com/other,{SUB_URL}",
                    ),
                ],
                rss=[make_rss_item(url=SUB_URL, aggregate=False)],
            )
            manager = TorrentManager(db)

            await manager.delete_rule(1, file=False)

            assert await db.rss.search_url(SUB_URL) is not None

    async def test_delete_rule_comma_joined_link_removes_each_orphan_feed(
        self, db_engine
    ):
        url_a = "https://mikanani.me/RSS/Bangumi?bangumiId=1"
        url_b = "https://mikanani.me/RSS/Bangumi?bangumiId=2"
        async with Database(engine=db_engine) as db:
            await _seed(
                db,
                bangumi=[make_bangumi(id=1, rss_link=f"{url_a},{url_b}")],
                rss=[
                    make_rss_item(url=url_a, aggregate=False),
                    make_rss_item(url=url_b, aggregate=False),
                ],
            )
            manager = TorrentManager(db)

            await manager.delete_rule(1, file=False)

            assert await db.rss.search_url(url_a) is None
            assert await db.rss.search_url(url_b) is None
