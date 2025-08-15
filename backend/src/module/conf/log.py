import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import settings

LOG_ROOT = Path("data")
LOG_PATH = LOG_ROOT / "log.txt"


def setup_logger(level: int = logging.INFO, reset: bool = False):
    level = logging.DEBUG if settings.log.debug_enable else level
    LOG_ROOT.mkdir(exist_ok=True)
    if reset and LOG_PATH.exists():
        LOG_PATH.unlink(missing_ok=True)

    logging.addLevelName(logging.DEBUG, "DEBUG:")
    logging.addLevelName(logging.INFO, "INFO:")
    logging.addLevelName(logging.WARNING, "WARNING:")
    LOGGING_FORMAT = "[%(asctime)s] %(levelname)-8s %(message)s"
    TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

    # 获取根日志器
    root_logger = logging.getLogger()

    # 如果已经有处理器且不是重置模式，则更新现有配置
    if root_logger.handlers and not reset:
        # 更新根日志器的等级
        root_logger.setLevel(level)
        # 更新所有处理器的等级
        for handler in root_logger.handlers:
            handler.setLevel(level)
    else:
        # 首次配置或重置模式，使用 basicConfig
        logging.basicConfig(
            level=level,
            format=LOGGING_FORMAT,
            datefmt=TIME_FORMAT,
            encoding="utf-8",
            handlers=[
                RotatingFileHandler(
                    LOG_PATH,
                    maxBytes=10 * 1024 * 1024,  # 10MB
                    backupCount=5,
                    encoding="utf-8",
                ),
                logging.StreamHandler(),
            ],
            force=reset,  # 强制重新配置如果是重置模式
        )
    loggers_to_silence = [
        "httpx",
        "httpcore",
        "hpack",
        "hpack.hpack",
        "passlib",
        "multipart",
        "multipart.multipart",
    ]
    for logger_name in loggers_to_silence:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)

    # 对于 bcrypt 有一个 适配的问题,就藏起来吧
    logging.getLogger("passlib").setLevel(logging.ERROR)
