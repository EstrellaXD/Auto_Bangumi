import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_, delete, select

from module.models import RSSItem, RSSUpdate

logger = logging.getLogger(__name__)


class RSSDatabase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, data: RSSItem) -> bool:
        statement = select(RSSItem).where(RSSItem.url == data.url)
        result = await self.session.execute(statement)
        db_data = result.scalar_one_or_none()
        if db_data:
            logger.debug(f"RSS Item {data.url} already exists.")
            return False
        else:
            logger.debug(f"RSS Item {data.url} not exists, adding...")
            self.session.add(data)
            await self.session.commit()
            await self.session.refresh(data)
            return True

    async def add_all(self, data: list[RSSItem]):
        if not data:
            return
        urls = [item.url for item in data]
        statement = select(RSSItem.url).where(RSSItem.url.in_(urls))
        result = await self.session.execute(statement)
        existing_urls = set(result.scalars().all())
        new_items = [item for item in data if item.url not in existing_urls]
        if new_items:
            self.session.add_all(new_items)
            await self.session.commit()
            logger.debug(f"Batch inserted {len(new_items)} RSS items.")

    async def update(self, _id: int, data: RSSUpdate) -> bool:
        statement = select(RSSItem).where(RSSItem.id == _id)
        result = await self.session.execute(statement)
        db_data = result.scalar_one_or_none()
        if not db_data:
            return False
        dict_data = data.dict(exclude_unset=True)
        for key, value in dict_data.items():
            setattr(db_data, key, value)
        self.session.add(db_data)
        await self.session.commit()
        return True

    async def enable(self, _id: int) -> bool:
        statement = select(RSSItem).where(RSSItem.id == _id)
        result = await self.session.execute(statement)
        db_data = result.scalar_one_or_none()
        if not db_data:
            return False
        db_data.enabled = True
        self.session.add(db_data)
        await self.session.commit()
        return True

    async def disable(self, _id: int) -> bool:
        statement = select(RSSItem).where(RSSItem.id == _id)
        result = await self.session.execute(statement)
        db_data = result.scalar_one_or_none()
        if not db_data:
            return False
        db_data.enabled = False
        self.session.add(db_data)
        await self.session.commit()
        return True

    async def search_id(self, _id: int) -> RSSItem | None:
        return await self.session.get(RSSItem, _id)

    async def search_all(self) -> list[RSSItem]:
        result = await self.session.execute(select(RSSItem))
        return list(result.scalars().all())

    async def search_active(self) -> list[RSSItem]:
        result = await self.session.execute(
            select(RSSItem).where(RSSItem.enabled)
        )
        return list(result.scalars().all())

    async def search_aggregate(self) -> list[RSSItem]:
        result = await self.session.execute(
            select(RSSItem).where(and_(RSSItem.aggregate, RSSItem.enabled))
        )
        return list(result.scalars().all())

    async def delete(self, _id: int) -> bool:
        condition = delete(RSSItem).where(RSSItem.id == _id)
        try:
            await self.session.execute(condition)
            await self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Delete RSS Item failed. Because: {e}")
            return False

    async def delete_all(self):
        condition = delete(RSSItem)
        await self.session.execute(condition)
        await self.session.commit()
