import logging
import re

from urllib3.util import parse_url

from module.network import RequestContent
from module.rss import RSSEngine
from module.utils import save_image

logger = logging.getLogger(__name__)


async def from_30_to_31():
    with RSSEngine() as db:
        db.migrate()
        # Update poster link
        bangumis = db.bangumi.search_all()
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
        db.bangumi.update_all(bangumis)
        for rss in rss_pool:
            if "mybangumi" in rss.lower():
                aggregate = True
            else:
                aggregate = False
            await db.add_rss(rss_link=rss, aggregate=aggregate)


async def from_31_to_32():
    """Migrate database schema from 3.1.x to 3.2.x."""
    with RSSEngine() as db:
        db.create_table()
        db.run_migrations()
    logger.info("[Migration] 3.1 -> 3.2 migration completed.")


def run_migrations():
    """Check schema version and run any pending migrations."""
    with RSSEngine() as db:
        db.run_migrations()


async def cache_image():
    with RSSEngine() as db:
        bangumis = db.bangumi.search_all()
        async with RequestContent() as req:
            for bangumi in bangumis:
                if bangumi.poster_link:
                    # Hash local path
                    img = await req.get_content(bangumi.poster_link)
                    suffix = bangumi.poster_link.split(".")[-1]
                    img_path = save_image(img, suffix)
                    bangumi.poster_link = img_path
        db.bangumi.update_all(bangumis)
