import logging

from sqlmodel import Session, and_, delete, select

from models import RSSItem

logger = logging.getLogger(__name__)


class RSSDatabase:
    """
    RSS 是一切的开始, bangumi 和 torrent 都以 rss 为外键
    rss 的主码是 rss_link, id
    现在是 rss 的 id 变动时, bangumi 和 torrent 的 rss_id 也要变动
    """

    def __init__(self, session: Session):
        self.session = session

    def add(self, data: RSSItem):
        # Check if exists
        if data.id is None:
            statement = select(RSSItem).where(RSSItem.url == data.url)
            logger.debug(f"[RSSDatabase] Searching for RSS Item: {data.url}")
            db_data = self.session.exec(statement).first()
            if db_data:
                logger.debug(f"RSS Item {data.url} already exists, updating...")
                data.id = db_data.id
                return False
        logger.debug(f"[RSSDatabase] updating RSS Item: {data.url}")
        self.session.merge(data)
        self.session.commit()
        return True

    def add_all(self, data: list[RSSItem]):
        for item in data:
            self.add(item)

    def update(self, data: RSSItem):
        self.session.merge(data)
        self.session.commit()
        return True

    def enable(self, _id: int):
        db_data = self.session.get(RSSItem, _id)
        if not db_data:
            return False
        db_data.enabled = True
        self.session.add(db_data)
        self.session.commit()
        self.session.refresh(db_data)
        return True

    def disable(self, _id: int):
        db_data = self.session.get(RSSItem, _id)
        if not db_data:
            return False
        db_data.enabled = False
        self.session.add(db_data)
        self.session.commit()
        self.session.refresh(db_data)
        return True

    def search_id(self, _id: int) -> RSSItem|None:
        return self.session.get(RSSItem, _id)

    def search_all(self) -> list[RSSItem]:
        return list(self.session.exec(select(RSSItem)).all())

    def search_active(self) -> list[RSSItem]:
        return list(self.session.exec(select(RSSItem).where(RSSItem.enabled)).all())

    def search_url(self, rss_link: str) -> RSSItem | None:
        statement = select(RSSItem).where(RSSItem.url == rss_link)
        rssitem = self.session.exec(statement).first()
        if rssitem is None:
            logger.warning(f"[Database] Cannot find rssitem link: {rss_link}.")
            return None
        else:
            logger.debug(f"[Database] Find bangumi id: {rss_link}.")
            return self.session.exec(statement).first()

    def delete(self, _id: int) -> bool:
        # condition = delete(RSSItem).where(RSSItem.id == _id)
        rss_item = self.session.get(RSSItem, _id)
        if not rss_item:
            logger.error(f"Delete RSS Item failed. Can't find id: {_id}")
            return False
        try:
            self.session.delete(rss_item)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Delete RSS Item failed. Because: {e}")
            return False
