import logging

from module.database import Database
from module.downloader import AddResult, DownloadClient
from module.models import Bangumi, ResponseModel
from module.network import RequestContent
from module.rss import RSSEngine
from module.searcher import SearchTorrent

logger = logging.getLogger(__name__)


async def _ensure_bangumi_id(db: Database, data: Bangumi) -> bool:
    """确保 ``data.id`` 可用：新番剧插入拿 id，重复番剧解析出已存在行的 id。

    ``add()`` 对精确重复（title_raw+group_name）与语义重复（并入别名）都
    返回 False 且不回填 id——不解析已存在行的话，add_torrent 的 ab:<id>
    标签与种子行的 bangumi_id 关联都会丢失，种子被记成孤儿。

    解析到被软删除（禁用）的行时会重新启用它：显式订阅/收集一个已禁用
    的规则只能是用户想要它回来——不启用的话种子要么变孤儿、要么挂到
    对下游所有查询都不可见的行上。传入的 id 指向已不存在的行时清空，
    避免种子挂到悬空外键。返回是否插入了新行（调用方据此决定失败时
    是否回滚删除）。
    """
    if await db.bangumi.add(data):
        return True
    existing = await db.bangumi.find_duplicate(data)
    if existing is None:
        existing = await db.bangumi.find_semantic_duplicate(data)
    if existing is not None:
        if existing.deleted:
            await db.bangumi.restore_one(existing.id)
        data.id = existing.id
    elif data.id is not None and await db.bangumi.search_id(data.id) is None:
        data.id = None  # type: ignore[assignment]
    return False


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
            inserted = False
            if bangumi.id is None or not await db.bangumi.update(bangumi):
                inserted = await _ensure_bangumi_id(db, bangumi)
            else:
                # 载荷带着已禁用行的 id 也能 update 成功：显式收集
                # 即用户想重新启用，否则种子会挂到不可见的行上
                await db.bangumi.restore_one(bangumi.id)
            if await self.client.add_torrent(torrents, bangumi) is AddResult.ADDED:
                logger.info(
                    f"Collections of {bangumi.official_title} Season {bangumi.season} completed."
                )
                for torrent in torrents:
                    torrent.downloaded = True
                    torrent.bangumi_id = bangumi.id
                bangumi.eps_collect = True
                # 只更新 eps_collect 单个字段：解析到已存在行时，整行
                # update 会用刚解析的默认值覆盖用户调好的 offset/filter
                if bangumi.id is not None:
                    await db.bangumi.mark_eps_collect(bangumi.id)
                await db.torrent.add_all(torrents)
                return ResponseModel(
                    status=True,
                    status_code=200,
                    msg_en=f"Collections of {bangumi.official_title} Season {bangumi.season} completed.",
                    msg_zh=f"收集 {bangumi.official_title} 第 {bangumi.season} 季完成。",
                )
            else:
                if inserted and bangumi.id is not None:
                    # 收集失败时回滚刚插入的行，不留下幽灵订阅规则
                    await db.bangumi.delete_one(bangumi.id)
                    bangumi.id = None  # type: ignore[assignment]
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
