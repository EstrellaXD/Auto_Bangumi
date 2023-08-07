from sqlmodel import Session, SQLModel

from .rss import RSSDatabase
from .torrent import TorrentDatabase
from .bangumi import BangumiDatabase
from .user import UserDatabase
from .engine import engine as e


class Database(Session):
    def __init__(self, engine=e):
        self.engine = engine
        super().__init__(engine)
        self.rss = RSSDatabase(self)
        self.torrent = TorrentDatabase(self)
        self.bangumi = BangumiDatabase(self)
        self.user = UserDatabase(self)

    def create_table(self):
        SQLModel.metadata.create_all(self.engine)

    def drop_table(self):
        SQLModel.metadata.drop_all(self.engine)

    def migrate(self):
        # Run migration online
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
