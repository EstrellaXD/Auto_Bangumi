import logging
from conf import settings


def setup_logger():
    level = logging.DEBUG if settings.debug_mode else logging.INFO
    LOGGING_FORMAT = "[%(asctime)s] %(levelname)s:\t%(message)s"
    logging.basicConfig(
        level=level,
        format=LOGGING_FORMAT,
        encoding="utf-8",
        handlers=[
            logging.FileHandler(settings.log_path),
            logging.StreamHandler(),
        ]
    )
