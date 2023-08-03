import logging

from sqlmodel import Session, select, delete

from .engine import engine
from module.models import RSSItem

logger = logging.getLogger(__name__)


class RSSDatabase:
    def __init__(self, session: Session):
        self.session = session

    def insert_one(self, data: RSSItem):
        self.session.add(data)
        self.session.commit()
        self.session.refresh(data)

    def search_all(self) -> list[RSSItem]:
        return self.session.exec(select(RSSItem)).all()

    def delete_one(self, _id: int):
        condition = delete(RSSItem).where(RSSItem.id == _id)
        self.session.exec(condition)
        self.session.commit()

    def delete_all(self):
        condition = delete(RSSItem)
        self.session.exec(condition)
        self.session.commit()


