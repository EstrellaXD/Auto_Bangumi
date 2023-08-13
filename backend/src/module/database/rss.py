import logging

from sqlmodel import Session, select, delete, and_

from module.models import RSSItem, RSSUpdate

logger = logging.getLogger(__name__)


class RSSDatabase:
    def __init__(self, session: Session):
        self.session = session

    def add(self, data: RSSItem):
        # Check if exists
        statement = select(RSSItem).where(RSSItem.url == data.url)
        db_data = self.session.exec(statement).first()
        if db_data:
            logger.debug(f"RSS Item {data.url} already exists.")
            return False
        else:
            logger.debug(f"RSS Item {data.url} not exists, adding...")
            self.session.add(data)
            self.session.commit()
            self.session.refresh(data)
            return True

    def add_all(self, data: list[RSSItem]):
        for item in data:
            self.add(item)

    def update(self, _id: int, data: RSSUpdate):
        # Check if exists
        statement = select(RSSItem).where(RSSItem.id == _id)
        db_data = self.session.exec(statement).first()
        if not db_data:
            return False
        # Update
        dict_data = data.dict(exclude_unset=True)
        for key, value in dict_data.items():
            setattr(db_data, key, value)
        self.session.add(db_data)
        self.session.commit()
        self.session.refresh(db_data)
        return True

    def search_id(self, _id: int) -> RSSItem:
        return self.session.get(RSSItem, _id)

    def search_all(self) -> list[RSSItem]:
        return self.session.exec(select(RSSItem)).all()

    def search_active(self) -> list[RSSItem]:
        return self.session.exec(select(RSSItem).where(RSSItem.enabled)).all()

    def search_aggregate(self) -> list[RSSItem]:
        return self.session.exec(
            select(RSSItem).where(and_(RSSItem.aggregate, RSSItem.enabled))
        ).all()

    def delete(self, _id: int):
        condition = delete(RSSItem).where(RSSItem.id == _id)
        self.session.exec(condition)
        self.session.commit()

    def delete_all(self):
        condition = delete(RSSItem)
        self.session.exec(condition)
        self.session.commit()
