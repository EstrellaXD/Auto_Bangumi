import logging

from sqlmodel import Session, select, delete

from .engine import engine
from module.models import RSSItem

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
            return
        else:
            logger.debug(f"RSS Item {data.url} not exists, adding...")
            self.session.add(data)
            self.session.commit()
            self.session.refresh(data)

    def update(self, data: RSSItem):
        self.session.add(data)
        self.session.commit()
        self.session.refresh(data)

    # TODO: Check if this is needed
    def search_id(self, _id: int) -> RSSItem:
        return self.session.get(RSSItem, _id)

    def search_all(self) -> list[RSSItem]:
        return self.session.exec(select(RSSItem)).all()

    def search_active(self) -> list[RSSItem]:
        return self.session.exec(select(RSSItem).where(RSSItem.enabled)).all()

    def search_combine(self) -> list[RSSItem]:
        return self.session.exec(select(RSSItem).where(RSSItem.combine)).all()

    def delete(self, _id: int):
        condition = delete(RSSItem).where(RSSItem.id == _id)
        self.session.exec(condition)
        self.session.commit()

    def delete_all(self):
        condition = delete(RSSItem)
        self.session.exec(condition)
        self.session.commit()
