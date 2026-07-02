import logging

from module.conf import POSTERS_PATH
from module.database import Database

logger = logging.getLogger(__name__)


async def start_up():
    async with Database() as db:
        await db.create_table()
        await db.run_migrations()
        await db.user.add_default_user()


async def first_run():
    async with Database() as db:
        await db.create_table()
        await db.run_migrations()
        await db.user.add_default_user()
    POSTERS_PATH.mkdir(parents=True, exist_ok=True)
