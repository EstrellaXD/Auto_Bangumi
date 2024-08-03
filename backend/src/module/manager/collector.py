import logging

from module.database import Database, engine
from module.downloader import DownloadClient
from module.models import Bangumi, ResponseModel
from module.rss import RSSEngine, RSSManager
from module.searcher import SearchTorrent

logger = logging.getLogger(__name__)


class SeasonCollector():
    def __init__(self):
        self.st = SearchTorrent()
        self.rss_engine = RSSEngine() 

    async def collect_season(self, bangumi: Bangumi, link: str = None):
        logger.info(
            f"Start collecting {bangumi.official_title} Season {bangumi.season}..."
        )
        # with SearchTorrent() as st, RSSEngine() as engine:

        if not link:
            torrents = await self.st.search_season(bangumi)
        else:
            async with self.st.req() as req:
                torrents = await req.get_torrents(link, bangumi.filter.replace(",", "|"))

        async with DownloadClient() as client:
            if await client.add_torrents(torrents, bangumi):
                logger.info(
                    f"Collections of {bangumi.official_title} Season {bangumi.season} completed."
                )
                # for torrent in torrents:
                #     torrent.downloaded = True
                bangumi.eps_collect = True
                with Database(engine) as db:
                    if db.bangumi.update(bangumi):
                        db.bangumi.add(bangumi)
                    db.torrent.add_all(torrents)
                return ResponseModel(
                    status=True,
                    status_code=200,
                    msg_en=f"Collections of {bangumi.official_title} Season {bangumi.season} completed.",
                    msg_zh=f"收集 {bangumi.official_title} 第 {bangumi.season} 季完成。",
                )
            else:
                logger.warning(
                    f"Already collected {bangumi.official_title} Season {bangumi.season}."
                )
                return ResponseModel(
                    status=False,
                    status_code=406,
                    msg_en=f"Collection of {bangumi.official_title} Season {bangumi.season} failed.",
                    msg_zh=f"收集 {bangumi.official_title} 第 {bangumi.season} 季失败, 种子已经添加。",
                )

    @staticmethod
    async def subscribe_season(data: Bangumi,parser:str = "mikan"):
        data.added = True
        data.eps_collect = True
        await RSSManager().add_rss(
            rss_link=data.rss_link, name=data.official_title, aggregate=False
        )
        result = await RSSEngine().download_bangumi(data)
        return result


async def eps_complete():
    # with RSSEngine() as engine:
    with Database(engine) as db:
        datas = db.bangumi.not_complete()
        if datas:
            logger.info("Start collecting full season...")
            for data in datas:
                if not data.eps_collect:
                    # with SeasonCollector() as collector:
                    collector = SeasonCollector()
                    await collector.collect_season(data)
                data.eps_collect = True
            db.bangumi.update_all(datas)

if __name__ == "__main__":
    import asyncio
    # async def subscrib_s():
    #     # t = RSSItem(url=link)
    #     return await analysis(t)

    official_title = "败犬女主太多了！"
    rss_link = "https://mikanani.me/RSS/Bangumi?bangumiId=3391&subgroupid=583"
    t = Bangumi(official_title=official_title,rss_link=rss_link)
    ans = asyncio.run(SeasonCollector().subscribe_season(t))
    # print(ans)
