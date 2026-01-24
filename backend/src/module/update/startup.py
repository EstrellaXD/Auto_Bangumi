import logging

from module.conf import POSTERS_PATH
from module.rss import RSSEngine

logger = logging.getLogger(__name__)


def start_up():
    with RSSEngine() as engine:
        engine.create_table()
        engine.run_migrations()
        engine.user.add_default_user()


def first_run():
    with RSSEngine() as engine:
        engine.create_table()
        engine.run_migrations()
        engine.user.add_default_user()
    POSTERS_PATH.mkdir(parents=True, exist_ok=True)
