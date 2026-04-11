import atexit
import logging
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path
from queue import SimpleQueue

from .config import settings

LOG_ROOT = Path("data")
LOG_PATH = LOG_ROOT / "log.txt"

_listener: QueueListener | None = None


def setup_logger(level: int = logging.INFO, reset: bool = False):
    global _listener

    level = logging.DEBUG if settings.log.debug_enable else level
    LOG_ROOT.mkdir(exist_ok=True)

    if reset and LOG_PATH.exists():
        LOG_PATH.unlink(missing_ok=True)

    logging.addLevelName(logging.DEBUG, "DEBUG:")
    logging.addLevelName(logging.INFO, "INFO:")
    logging.addLevelName(logging.WARNING, "WARNING:")
    LOGGING_FORMAT = "[%(asctime)s] %(levelname)-8s  %(message)s"
    TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(LOGGING_FORMAT, datefmt=TIME_FORMAT)

    file_handler = RotatingFileHandler(
        LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    log_queue: SimpleQueue = SimpleQueue()
    queue_handler = QueueHandler(log_queue)

    _listener = QueueListener(log_queue, file_handler, stream_handler, respect_handler_level=True)
    _listener.start()
    atexit.register(_listener.stop)

    logging.basicConfig(
        level=level,
        handlers=[queue_handler],
    )

    # Suppress verbose HTTP request logs from httpx and httpcore
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
