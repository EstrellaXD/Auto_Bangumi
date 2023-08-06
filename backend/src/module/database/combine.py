from sqlmodel import Session, SQLModel

from .rss import RSSDatabase
from .torrent import TorrentDatabase
from .bangumi import BangumiDatabase
from .engine import engine as e


class Database(Session):
    def __init__(self, engine=e):
        self.engine = engine
        super().__init__(engine)
        self.rss = RSSDatabase(self)
        self.torrent = TorrentDatabase(self)
        self.bangumi = BangumiDatabase(self)

    def create_table(self):
        SQLModel.metadata.create_all(self.engine)
