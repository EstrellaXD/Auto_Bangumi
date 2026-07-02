import logging

from sqlmodel import Session, SQLModel

from module.models import Bangumi, User

from .bangumi import BangumiDatabase
from .engine import engine as e
from .migrations import (  # noqa: F401  (re-exported for existing importers)
    CURRENT_SCHEMA_VERSION,
    MIGRATIONS,
    TABLE_MODELS,
    create_tables,
    run_migrations,
)
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
        create_tables(self.engine)

    def run_migrations(self):
        run_migrations(self.engine)

    def drop_table(self):
        SQLModel.metadata.drop_all(self.engine)

    def migrate(self):
        # Run migration online
        bangumi_data = self.bangumi.search_all()
        user_data = self.exec("SELECT * FROM user").all()
        if not user_data:
            logger.warning("[Database] No user data found, skipping migration.")
            return
        readd_bangumi = []
        for bangumi in bangumi_data:
            dict_data = bangumi.dict()
            del dict_data["id"]
            readd_bangumi.append(Bangumi(**dict_data))
        self.drop_table()
        self.create_table()
        self.commit()
        try:
            self.bangumi.add_all(readd_bangumi)
            self.add(User(**user_data[0]))
            self.commit()
        except Exception:
            self.rollback()
            raise
