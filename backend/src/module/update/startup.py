import logging

from module.conf import POSTERS_PATH
from module.database import Database
from module.network import RequestContent
from module.utils import save_image

logger = logging.getLogger(__name__)


async def first_run():
    async with Database() as db:
        await db.create_table()
        await db.run_migrations()
        await db.user.add_default_user()
    POSTERS_PATH.mkdir(parents=True, exist_ok=True)


async def run_migrations():
    """补建缺失的表，再执行待应用的 schema 迁移；两步都是幂等的。"""
    async with Database() as db:
        await db.create_table()
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
                        img_path = await save_image(
                            img, suffix, source_url=bangumi.poster_link
                        )
                        if img_path:
                            bangumi.poster_link = img_path
                    except Exception as e:
                        logger.warning(
                            "Failed to cache poster for %s: %s",
                            bangumi.official_title,
                            e,
                        )
        await db.bangumi.update_all(bangumis)
