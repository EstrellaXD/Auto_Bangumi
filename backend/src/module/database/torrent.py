import logging
from collections import defaultdict

from sqlalchemy import delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_, col, select, true

from module.models import Bangumi, RSSItem, Torrent

logger = logging.getLogger(__name__)


class TorrentDatabase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, data: Torrent):
        self.session.add(data)
        await self.session.commit()
        logger.debug("Insert %s in database.", data.name)

    async def add_all(self, datas: list[Torrent]):
        self.session.add_all(datas)
        await self.session.commit()
        logger.debug("Insert %s torrents in database.", len(datas))

    async def update(self, data: Torrent):
        self.session.add(data)
        await self.session.commit()
        logger.debug("Update %s in database.", data.name)

    async def update_all(self, datas: list[Torrent]):
        self.session.add_all(datas)
        await self.session.commit()

    async def search(self, _id: int) -> Torrent | None:
        result = await self.session.execute(select(Torrent).where(Torrent.id == _id))
        return result.scalar_one_or_none()

    async def search_all(self) -> list[Torrent]:
        result = await self.session.execute(select(Torrent))
        return list(result.scalars().all())

    async def search_rss(self, rss_id: int) -> list[Torrent]:
        result = await self.session.execute(
            select(Torrent).where(Torrent.rss_id == rss_id)
        )
        return list(result.scalars().all())

    async def check_new(
        self, torrents_list: list[Torrent], rss: RSSItem | None = None
    ) -> list[Torrent]:
        """返回库中没有记录的种子。

        给出 ``rss`` 时只看该订阅已匹配、且所属番剧的 ``rss_link`` 已包含该
        订阅当前 URL 的记录（与 BangumiDatabase.match_list 的追加判断一致）：
        未匹配的孤儿每轮仍要重新分析，新番或上次分析失败的种子才能生成规则；
        订阅改了 URL 时仍要匹配，才能把新 URL 追加到 rss_link（#1053）。
        """
        if not torrents_list:
            return []
        urls = [t.url for t in torrents_list]
        # SQLModel 类属性在 mypy 看来是普通字段类型而非 InstrumentedAttribute，
        # 无法识别 .in_()/.is_() 等查询方法（无官方 mypy 插件支持）。
        statement = select(Torrent.url).where(Torrent.url.in_(urls))  # type: ignore[attr-defined]
        if rss is not None:
            # instr 区分大小写，与 Python 的 ``in`` 一致（LIKE 不区分）
            statement = statement.join(
                Bangumi,
                Bangumi.id == Torrent.bangumi_id,  # type: ignore[arg-type]
            ).where(
                Torrent.rss_id == rss.id,
                func.instr(Bangumi.rss_link, rss.url) > 0,
            )
        result = await self.session.execute(statement)
        existing_urls = set(result.scalars().all())
        return [t for t in torrents_list if t.url not in existing_urls]

    async def search_by_qb_hashes(self, qb_hashes: list[str]) -> list[Torrent]:
        """Find torrents by multiple qBittorrent hashes (batch query)."""
        if not qb_hashes:
            return []
        result = await self.session.execute(
            select(Torrent).where(Torrent.qb_hash.in_(qb_hashes))  # type: ignore[union-attr]
        )
        return list(result.scalars().all())

    async def search_by_bangumi_id(self, bangumi_id: int) -> list[Torrent]:
        """Find all torrent records associated with a bangumi."""
        result = await self.session.execute(
            select(Torrent).where(Torrent.bangumi_id == bangumi_id)
        )
        return list(result.scalars().all())

    async def search_downloaded_by_bangumi_ids(
        self, bangumi_ids: list[int]
    ) -> dict[int, list[Torrent]]:
        """Batch lookup already-downloaded torrents for the given bangumi ids.

        Used by the release-preference dedup path to compare an incoming
        candidate against what has already been downloaded for that episode,
        without a query per bangumi.
        """
        if not bangumi_ids:
            return {}
        result = await self.session.execute(
            select(Torrent).where(
                and_(
                    Torrent.bangumi_id.in_(bangumi_ids),  # type: ignore[union-attr]
                    Torrent.downloaded == true(),
                )
            )
        )
        grouped: dict[int, list[Torrent]] = defaultdict(list)
        for torrent in result.scalars().all():
            if torrent.bangumi_id is not None:
                grouped[torrent.bangumi_id].append(torrent)
        return dict(grouped)

    async def delete_by_bangumi_id(self, bangumi_id: int) -> int:
        """Delete all torrent records associated with a bangumi.

        Returns the number of deleted records.
        """
        # 单条 DELETE：逐行 ORM 删除会拉长写事务，与其他写入争 SQLite 锁（#1113）
        result = await self.session.execute(
            delete(Torrent)
            .where(col(Torrent.bangumi_id) == bangumi_id)
            .execution_options(synchronize_session=False)
        )
        await self.session.commit()
        count = result.rowcount  # type: ignore[attr-defined]
        if count > 0:
            logger.debug(
                "Deleted %s torrent records for bangumi_id %s.", count, bangumi_id
            )
        return count

    async def search_orphans(self) -> list[Torrent]:
        """Find all torrent records not associated with any bangumi."""
        result = await self.session.execute(
            select(Torrent).where(Torrent.bangumi_id.is_(None))  # type: ignore[union-attr]
        )
        return list(result.scalars().all())

    async def count_orphans(self) -> int:
        """Count torrent records not associated with any bangumi."""
        result = await self.session.execute(
            select(func.count())
            .select_from(Torrent)
            .where(Torrent.bangumi_id.is_(None))  # type: ignore[union-attr]
        )
        return result.scalar_one()

    async def delete_orphans(self) -> int:
        """Delete all torrent records not associated with any bangumi.

        Returns the number of deleted records.
        """
        result = await self.session.execute(
            delete(Torrent).where(Torrent.bangumi_id.is_(None))  # type: ignore[union-attr]
        )
        await self.session.commit()
        # execute(delete()) 返回 CursorResult，mypy 只能推断出基类 Result[Any]
        count = result.rowcount  # type: ignore[attr-defined]
        if count > 0:
            logger.debug("Deleted %s orphan torrents.", count)
        return count

    async def delete_obj(self, torrent: Torrent) -> None:
        """Delete a single torrent record."""
        await self.session.delete(torrent)
        await self.session.commit()
        logger.debug("Deleted torrent %s.", torrent.id)
