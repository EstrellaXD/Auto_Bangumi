import logging

from sqlmodel import Session, and_, delete, select

from module.models import RSSItem, RSSUpdate, Torrent

logger = logging.getLogger(__name__)


class RSSDatabase:
    def __init__(self, session: Session):
        self.session = session

    def add(self, data: RSSItem) -> bool:
        statement = select(RSSItem).where(RSSItem.url == data.url)
        result = self.session.execute(statement)
        db_data = result.scalar_one_or_none()
        if db_data:
            logger.debug("RSS Item %s already exists.", data.url)
            return False
        else:
            logger.debug("RSS Item %s not exists, adding...", data.url)
            self.session.add(data)
            self.session.commit()
            self.session.refresh(data)
            return True

    def add_all(self, data: list[RSSItem]):
        if not data:
            return
        urls = [item.url for item in data]
        statement = select(RSSItem.url).where(RSSItem.url.in_(urls))
        result = self.session.execute(statement)
        existing_urls = set(result.scalars().all())
        new_items = [item for item in data if item.url not in existing_urls]
        if new_items:
            self.session.add_all(new_items)
            self.session.commit()
            logger.debug("Batch inserted %s RSS items.", len(new_items))

    def update(self, _id: int, data: RSSUpdate) -> bool:
        statement = select(RSSItem).where(RSSItem.id == _id)
        result = self.session.execute(statement)
        db_data = result.scalar_one_or_none()
        if not db_data:
            return False
        dict_data = data.dict(exclude_unset=True)
        for key, value in dict_data.items():
            setattr(db_data, key, value)
        self.session.add(db_data)
        self.session.commit()
        return True

    def enable(self, _id: int) -> bool:
        statement = select(RSSItem).where(RSSItem.id == _id)
        result = self.session.execute(statement)
        db_data = result.scalar_one_or_none()
        if not db_data:
            return False
        db_data.enabled = True
        self.session.add(db_data)
        self.session.commit()
        return True

    def enable_batch(self, ids: list[int]):
        statement = select(RSSItem).where(RSSItem.id.in_(ids))
        result = self.session.execute(statement)
        for item in result.scalars().all():
            item.enabled = True
        self.session.commit()

    def disable(self, _id: int) -> bool:
        statement = select(RSSItem).where(RSSItem.id == _id)
        result = self.session.execute(statement)
        db_data = result.scalar_one_or_none()
        if not db_data:
            return False
        db_data.enabled = False
        self.session.add(db_data)
        self.session.commit()
        return True

    def disable_batch(self, ids: list[int]):
        statement = select(RSSItem).where(RSSItem.id.in_(ids))
        result = self.session.execute(statement)
        for item in result.scalars().all():
            item.enabled = False
        self.session.commit()

    def search_id(self, _id: int) -> RSSItem | None:
        return self.session.get(RSSItem, _id)

    def search_all(self) -> list[RSSItem]:
        result = self.session.execute(select(RSSItem))
        return list(result.scalars().all())

    def search_active(self) -> list[RSSItem]:
        result = self.session.execute(
            select(RSSItem).where(RSSItem.enabled)
        )
        return list(result.scalars().all())

    def search_aggregate(self) -> list[RSSItem]:
        result = self.session.execute(
            select(RSSItem).where(and_(RSSItem.aggregate, RSSItem.enabled))
        )
        return list(result.scalars().all())

    def delete(self, _id: int) -> bool:
        try:
            # 先删除引用该 RSS 的 torrent，避免外键约束报错
            self.session.execute(delete(Torrent).where(Torrent.rss_id == _id))
            self.session.execute(delete(RSSItem).where(RSSItem.id == _id))
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Delete RSS Item failed. Because: {e}")
            return False

    def delete_all(self):
        try:
            # 先删除所有引用 RSS 的 torrent，避免外键约束报错
            self.session.execute(delete(Torrent).where(Torrent.rss_id != None))  # noqa: E711
            self.session.execute(delete(RSSItem))
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.error(f"Delete all RSS Items failed. Because: {e}")
