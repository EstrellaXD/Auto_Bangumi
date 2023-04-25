import logging

from .config import settings

LOG_PATH = "data/log.txt"


def setup_logger():
    level = logging.DEBUG if settings.log.debug_enable else logging.INFO
    logging.addLevelName(logging.DEBUG, 'DEBUG:')
    logging.addLevelName(logging.INFO, 'INFO:')
    logging.addLevelName(logging.WARNING, 'WARNING:')
    LOGGING_FORMAT = "[%(asctime)s] %(levelname)-8s  %(message)s"
    logging.basicConfig(
        level=level,
        format=LOGGING_FORMAT,
        encoding="utf-8",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(),
        ]
    )
