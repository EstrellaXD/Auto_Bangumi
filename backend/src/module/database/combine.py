import logging

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel

from module.models import Bangumi, User
from module.models.passkey import Passkey

from .bangumi import BangumiDatabase
from .engine import engine as e
from .rss import RSSDatabase
from .torrent import TorrentDatabase
from .user import UserDatabase

logger = logging.getLogger(__name__)


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
        self._migrate_columns()

    def _migrate_columns(self):
        """Add new columns to existing tables if they don't exist."""
        inspector = inspect(self.engine)
        if "bangumi" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("bangumi")]
            if "air_weekday" not in columns:
                with self.engine.connect() as conn:
                    conn.execute(
                        text("ALTER TABLE bangumi ADD COLUMN air_weekday INTEGER")
                    )
                    conn.commit()
                logger.info("[Database] Migrated: added air_weekday column to bangumi table.")

    def drop_table(self):
        SQLModel.metadata.drop_all(self.engine)

    def migrate(self):
        # Run migration online
        bangumi_data = self.bangumi.search_all()
        user_data = self.exec("SELECT * FROM user").all()
        readd_bangumi = []
        for bangumi in bangumi_data:
            dict_data = bangumi.dict()
            del dict_data["id"]
            readd_bangumi.append(Bangumi(**dict_data))
        self.drop_table()
        self.create_table()
        self.commit()
        bangumi_data = self.bangumi.search_all()
        self.bangumi.add_all(readd_bangumi)
        self.add(User(**user_data[0]))
        self.commit()
