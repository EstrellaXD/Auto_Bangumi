import logging

from module.database import Database
from module.downloader import AddResult, DownloadClient
from module.models import Bangumi, ResponseModel
from module.network import RequestContent
from module.rss import RSSEngine
from module.searcher import SearchTorrent

logger = logging.getLogger(__name__)


async def _ensure_bangumi_id(db: Database, data: Bangumi) -> None:
    """确保 ``data.id`` 可用：新番剧插入拿 id，重复番剧解析出已存在行的 id。

    ``add()`` 对精确重复（title_raw+group_name）与语义重复（并入别名）都
    返回 False 且不回填 id——不解析已存在行的话，add_torrent 的 ab:<id>
    标签与种子行的 bangumi_id 关联都会丢失，种子被记成孤儿。
    """
    if await db.bangumi.add(data) or data.id is not None:
        return
    existing = await db.bangumi.find_duplicate(data)
    if existing is None:
        existing = await db.bangumi.find_semantic_duplicate(data)
    if existing is not None:
        data.id = existing.id


class SeasonCollector:
    def __init__(self, client: DownloadClient):
        self.client = client

    async def collect_season(self, bangumi: Bangumi, link: str | None = None):
        logger.info(
            f"Start collecting {bangumi.official_title} Season {bangumi.season}..."
        )
        st = SearchTorrent()
        if not link:
            torrents = await st.search_season(bangumi)
        else:
            async with RequestContent() as req:
                torrents = await req.get_torrents(
                    link, bangumi.filter.replace(",", "|")
                )
        async with Database() as db:
            # bangumi 必须先落库拿到 id：add_torrent 用它打 ab:<id> 标签，
            # 种子行也要用它关联 bangumi_id——否则种子会被记成孤儿，
            # track_orphans 开关对这些"已匹配"的种子完全失效。
            # update() returns False when no existing row matches
            # bangumi.id (i.e. this is a brand-new bangumi), in which
            # case it needs to be inserted (or resolved to the existing
            # duplicate row) instead.
            if bangumi.id is None or not await db.bangumi.update(bangumi):
                await _ensure_bangumi_id(db, bangumi)
            if await self.client.add_torrent(torrents, bangumi) is AddResult.ADDED:
                logger.info(
                    f"Collections of {bangumi.official_title} Season {bangumi.season} completed."
                )
                for torrent in torrents:
                    torrent.downloaded = True
                    torrent.bangumi_id = bangumi.id
                bangumi.eps_collect = True
                await db.bangumi.update(bangumi)
                await db.torrent.add_all(torrents)
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
    async def subscribe_season(data: Bangumi, parser: str = "mikan"):
        async with Database() as db:
            engine = RSSEngine(db)
            data.added = True
            data.eps_collect = True
            await engine.add_rss(
                rss_link=data.rss_link,
                name=data.official_title,
                aggregate=False,
                parser=parser,
            )
            # 先落库拿到 id（重复订阅时解析已存在行的 id）：download_bangumi
            # 里 add_torrent 的 ab:<id> 标签和种子行的 bangumi_id 关联都依赖它
            await _ensure_bangumi_id(db, data)
            return await engine.download_bangumi(data)


async def eps_complete():
    async with Database() as db:
        datas = await db.bangumi.not_complete()
        if datas:
            logger.info("Start collecting full season...")
            async with DownloadClient() as client:
                collector = SeasonCollector(client)
                for data in datas:
                    if not data.eps_collect:
                        await collector.collect_season(data)
                    data.eps_collect = True
            await db.bangumi.update_all(datas)
