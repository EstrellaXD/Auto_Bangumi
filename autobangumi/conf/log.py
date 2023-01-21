import logging
from autobangumi.conf import settings


def setup_logger():
    level = logging.DEBUG if settings.debug_mode else logging.INFO
    logging.addLevelName(logging.DEBUG, 'DEBUG:')
    logging.addLevelName(logging.INFO, 'INFO:')
    logging.addLevelName(logging.WARNING, 'WARNING:')
    LOGGING_FORMAT = "[%(asctime)s] %(levelname)-8s  %(message)s"
    logging.basicConfig(
        level=level,
        format=LOGGING_FORMAT,
        encoding="utf-8",
        handlers=[
            logging.FileHandler(settings.log_path),
            logging.StreamHandler(),
        ]
    )
