from sqlmodel import Session,SQLModel

from .engine import engine
from .rss import RSSDatabase
from .torrent import TorrentDatabase
from .bangumi import BangumiDatabase


class Database(Session):
    def __init__(self, _engine=engine):
        super().__init__(_engine)
        self.rss = RSSDatabase(self)
        self.torrent = TorrentDatabase(self)
        self.bangumi = BangumiDatabase(self)

    @staticmethod
    def create_table():
        SQLModel.metadata.create_all(engine)