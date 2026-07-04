import logging
import re

from urllib3.util import parse_url

from module.database import Database
from module.network import RequestContent
from module.rss import RSSEngine
from module.utils import save_image

logger = logging.getLogger(__name__)


async def from_30_to_31():
    async with Database() as db:
        engine = RSSEngine(db)
        await db.migrate()
        # Update poster link
        bangumis = await db.bangumi.search_all()
        rss_pool = []
        for bangumi in bangumis:
            if bangumi.poster_link:
                rss_link = bangumi.rss_link.split(",")[-1]
                if rss_link not in rss_pool and not re.search(
                    r"\d+.\d+.\d+.\d+", rss_link
                ):
                    rss_pool.append(rss_link)
                root_path = parse_url(rss_link).host
                if "://" not in bangumi.poster_link:
                    bangumi.poster_link = f"https://{root_path}{bangumi.poster_link}"
        await db.bangumi.update_all(bangumis)
        for rss in rss_pool:
            if "mybangumi" in rss.lower():
                aggregate = True
            else:
                aggregate = False
            await engine.add_rss(rss_link=rss, aggregate=aggregate)


async def from_31_to_32():
    """Migrate database schema from 3.1.x to 3.2.x."""
    async with Database() as db:
        await db.create_table()
        await db.run_migrations()
    logger.info("3.1 -> 3.2 migration completed.")


async def run_migrations():
    """Check schema version and run any pending migrations."""
    async with Database() as db:
        await db.run_migrations()


async def cache_image():
    async with Database() as db:
        bangumis = await db.bangumi.search_all()
        async with RequestContent() as req:
            for bangumi in bangumis:
                if bangumi.poster_link:
                    # Best-effort: a single dead/unreachable poster link must
                    # not abort the whole migration for every other bangumi.
                    try:
                        # Hash local path
                        img = await req.get_content(bangumi.poster_link)
                        suffix = bangumi.poster_link.split(".")[-1]
                        img_path = await save_image(img, suffix)
                        if img_path:
                            bangumi.poster_link = img_path
                    except Exception as e:
                        logger.warning(
                            "Failed to cache poster for %s: %s",
                            bangumi.official_title,
                            e,
                        )
        await db.bangumi.update_all(bangumis)
