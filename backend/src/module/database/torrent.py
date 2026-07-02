import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from module.models import Torrent

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

    async def update_one_user(self, data: Torrent):
        self.session.add(data)
        await self.session.commit()
        logger.debug("Update %s in database.", data.name)

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

    async def check_new(self, torrents_list: list[Torrent]) -> list[Torrent]:
        if not torrents_list:
            return []
        urls = [t.url for t in torrents_list]
        statement = select(Torrent.url).where(Torrent.url.in_(urls))
        result = await self.session.execute(statement)
        existing_urls = set(result.scalars().all())
        return [t for t in torrents_list if t.url not in existing_urls]

    async def search_by_qb_hash(self, qb_hash: str) -> Torrent | None:
        """Find torrent by qBittorrent hash."""
        result = await self.session.execute(
            select(Torrent).where(Torrent.qb_hash == qb_hash)
        )
        return result.scalar_one_or_none()

    async def search_by_qb_hashes(self, qb_hashes: list[str]) -> list[Torrent]:
        """Find torrents by multiple qBittorrent hashes (batch query)."""
        if not qb_hashes:
            return []
        result = await self.session.execute(
            select(Torrent).where(Torrent.qb_hash.in_(qb_hashes))
        )
        return list(result.scalars().all())

    async def delete_by_bangumi_id(self, bangumi_id: int) -> int:
        """Delete all torrent records associated with a bangumi.

        Returns the number of deleted records.
        """
        statement = select(Torrent).where(Torrent.bangumi_id == bangumi_id)
        result = await self.session.execute(statement)
        torrents = list(result.scalars().all())
        count = len(torrents)
        for t in torrents:
            await self.session.delete(t)
        if count > 0:
            await self.session.commit()
            logger.debug(
                "Deleted %s torrent records for bangumi_id %s.", count, bangumi_id
            )
        return count

    async def search_by_url(self, url: str) -> Torrent | None:
        """Find torrent by URL."""
        result = await self.session.execute(select(Torrent).where(Torrent.url == url))
        return result.scalar_one_or_none()

    async def update_qb_hash(self, torrent_id: int, qb_hash: str) -> bool:
        """Update the qb_hash for a torrent."""
        torrent = await self.search(torrent_id)
        if torrent:
            torrent.qb_hash = qb_hash
            self.session.add(torrent)
            await self.session.commit()
            logger.debug("Updated qb_hash for torrent %s: %s", torrent_id, qb_hash)
            return True
        return False
