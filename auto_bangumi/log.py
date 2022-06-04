import logging
from conf import settings

if settings.debug_mode:
    debug_level = logging.DEBUG
else:
    debug_level = logging.INFO

def setup_logger():
    DATE_FORMAT = "%Y-%m-%d %X"
    LOGGING_FORMAT = "%(asctime)s %(levelname)s: %(message)s"
    logging.basicConfig(
        level=debug_level,
        datefmt=DATE_FORMAT,
        format=LOGGING_FORMAT,
        encoding="utf-8",
    )
