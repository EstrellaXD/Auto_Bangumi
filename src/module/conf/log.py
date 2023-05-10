import logging

LOG_PATH = "data/log.txt"


def setup_logger(level):
    logging.addLevelName(logging.DEBUG, "DEBUG:")
    logging.addLevelName(logging.INFO, "INFO:")
    logging.addLevelName(logging.WARNING, "WARNING:")
    LOGGING_FORMAT = "[%(asctime)s] %(levelname)-8s  %(message)s"
    TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(
        level=level,
        format=LOGGING_FORMAT,
        datefmt=TIME_FORMAT,
        encoding="utf-8",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
