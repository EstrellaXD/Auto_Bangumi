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
        logger.debug(f"Insert {data.name} in database.")

    async def add_all(self, datas: list[Torrent]):
        self.session.add_all(datas)
        await self.session.commit()
        logger.debug(f"Insert {len(datas)} torrents in database.")

    async def update(self, data: Torrent):
        self.session.add(data)
        await self.session.commit()
        logger.debug(f"Update {data.name} in database.")

    async def update_all(self, datas: list[Torrent]):
        self.session.add_all(datas)
        await self.session.commit()

    async def update_one_user(self, data: Torrent):
        self.session.add(data)
        await self.session.commit()
        logger.debug(f"Update {data.name} in database.")

    async def search(self, _id: int) -> Torrent | None:
        result = await self.session.execute(
            select(Torrent).where(Torrent.id == _id)
        )
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
