import logging

from module.rss import RSSEngine
from module.conf import settings

logger = logging.getLogger(__name__)


def start_up():
    with RSSEngine() as engine:
        engine.create_table()
        engine.user.add_default_user()


def first_run():
    with RSSEngine() as engine:
        engine.create_table()
        engine.user.add_default_user()
