from module.database import Database
from module.rss import RSSEngine


def update_main_rss(rss_link: str):
    with Database() as db:
        engine = RSSEngine(db)
        engine.add_rss(rss_link, "main", True)
