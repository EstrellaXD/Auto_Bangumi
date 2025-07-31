import logging

from module.conf import POSTERS_PATH
from module.database import Database
from module.conf import DATA_PATH, VERSION_PATH

logger = logging.getLogger(__name__)


def start_up():
    with Database() as engine:
        engine.create_table()
        engine.user.add_default_user()


def first_run():
    with Database() as engine:
        engine.create_table()
        engine.user.add_default_user()
        version = "3.2.0"
        if VERSION_PATH.exists():
            version= VERSION_PATH.read_text().strip()
            logger.debug(f"Current version: {version}")
        engine.databaseversion.add(version=version, description="First run setup")
    POSTERS_PATH.mkdir(parents=True, exist_ok=True)
