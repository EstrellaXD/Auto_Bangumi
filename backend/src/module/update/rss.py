from module.database import Database
from module.rss import RSSEngine


async def update_main_rss(rss_link: str):
    async with Database() as db:
        engine = RSSEngine(db)
        await engine.add_rss(rss_link, "main", True)
