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


class Database:
    def __init__(self, engine=e):
        self.engine = engine
        self.session = Session(engine)
        self.rss = RSSDatabase(self.session)
        self.torrent = TorrentDatabase(self.session)
        self.bangumi = BangumiDatabase(self.session)
        self.user = UserDatabase(self.session)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    # Transitional session delegates for existing call sites that used to rely
    # on Database being a Session.
    def add(self, obj):
        self.session.add(obj)

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()

    def refresh(self, obj):
        self.session.refresh(obj)

    def close(self):
        self.session.close()

    def create_table(self):
        create_tables(self.engine)

    def run_migrations(self):
        run_migrations(self.engine)

    def drop_table(self):
        SQLModel.metadata.drop_all(self.engine)

    def migrate(self):
        # Run migration online
        bangumi_data = self.bangumi.search_all()
        user_data = self.session.exec("SELECT * FROM user").all()
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
