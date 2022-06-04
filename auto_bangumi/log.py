import logging


def setup_logger():
    DATE_FORMAT = "%Y-%m-%d %X"
    LOGGING_FORMAT = "%(asctime)s %(levelname)s: %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        datefmt=DATE_FORMAT,
        format=LOGGING_FORMAT,
        encoding="utf-8",
    )
