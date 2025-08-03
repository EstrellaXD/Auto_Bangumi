import logging

from module.conf import settings
from module.database import Database, engine
from module.downloader import DownloadQueue
from module.models import Bangumi, Torrent
from module.rss import RSSEngine, RSSManager
from module.rss.engine import BangumiRefresher
from module.searcher import SearchTorrent

from .bangumi import BangumiManager

logger = logging.getLogger(__name__)


class SeasonCollector:
    def __init__(self):
        self.st = SearchTorrent()
        self.rss_engine = RSSEngine()

    @staticmethod
    async def subscribe_season(data: Bangumi, parser: str = "mikan"):
        """
        主要用于订阅 rss subscribe, 订阅后会自动下载
        """
        data.added = True
        data.eps_collect = True
        await RSSManager().add_rss(
            rss_link=data.rss_link,
            name=data.official_title,
            aggregate=False,
            parser=parser,
        )
        # 当 解析失败的时候, 会没有海报
        if not data.poster_link:
            try:
                # 有mikan id,但 mikan 是不会失败的
                await BangumiManager().refind_poster(data)
            except Exception:
                logging.warning(f"[Engine] Fail to pull poster {data.official_title} ")
        with Database() as db:
            db.bangumi.add(data)
        result = await RSSEngine().download_bangumi(data)
        if result:
            return True
        return False


async def complete_season(data: Bangumi) -> list[Torrent] | None:
    if data.mikan_id and "#" in data.mikan_id:
        # https://mikanani.me/RSS/Bangumi?bangumiId=3649&subgroupid=370
        mikan_id = data.mikan_id.split("#")[0]
        group_id = data.mikan_id.split("#")[1]
        mikan_url = f"https://{settings.rss_parser.mikan_custom_url}/RSS/Bangumi?bangumiId={mikan_id}&subgroupid={group_id}"
    else:
        data.title_raw = data.title_raw.split(",")[0]
        mikan_url = SearchTorrent().special_url(data, "mikan").url
    url = data.rss_link
    data.rss_link = mikan_url
    ans = await BangumiRefresher(data)._get_torrents()
    if not ans:
        logger.warning(f"[eps_complete] {data.official_title} no torrents found")
        return None
    ans = await BangumiRefresher(data).refresh()
    data.rss_link = url
    return ans


async def eps_complete():
    # 一次只补一个,不然会炸 qb
    with Database(engine) as db:
        datas = db.bangumi.not_complete()
        if not datas:
            logger.debug("[eps] there is no bangumi need to be completed")
            return True
        logger.info("Start collecting full season...")
        data = datas[0]
        # 复制 data 到 temp_bangumi
        logger.debug(f"[eps_complete] {data.official_title} eps start to complete")
        try:
            if ans := await complete_season(data):
                await DownloadQueue().add_torrents(ans, data)
                data.eps_collect = True
                db.bangumi.update(data)
                logger.debug(f"[eps_complete] {data.official_title} eps is completed")
            else:
                logger.debug(
                    f"[eps_complete] {data.official_title} eps is not completed"
                )
        except Exception as e:
            logger.error(f"[eps_complete] {e}")


if __name__ == "__main__":
    import asyncio

    from module.conf import setup_logger
    from module.downloader import DownloadController

    setup_logger("DEBUG")

    async def test():
        t = Bangumi(official_title=official_title, rss_link=rss_link)
        asyncio.create_task(DownloadController().download())
        await eps_complete()
        await asyncio.sleep(20)

    official_title = "败犬女主太多了！"
    rss_link = "https://mikanani.me/RSS/Bangumi?bangumiId=3391&subgroupid=583"
    ans = asyncio.run(test())
