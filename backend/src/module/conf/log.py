import atexit
import logging
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path
from queue import SimpleQueue

from .config import settings

LOG_ROOT = Path("data")
LOG_PATH = LOG_ROOT / "log.txt"

# 日志总量上限：log.txt ≤ _MAX_BYTES，加 _BACKUP_COUNT 份轮转备份，
# 合计约 (1 + _BACKUP_COUNT) * _MAX_BYTES。
_MAX_BYTES = 2 * 1024 * 1024
_BACKUP_COUNT = 3

_listener: QueueListener | None = None


def rotate_boot_log() -> None:
    """启动时把上一次运行的日志轮转进备份（log.txt.1..N），而非删除。

    此前 reset 直接 unlink：每次容器重启/在线更新都清空全部历史，
    用户恰恰在重启后最需要查看之前发生了什么（#日志时有时无）。
    复用 RotatingFileHandler.doRollover 保证与运行时轮转的命名/淘汰
    逻辑完全一致（delay=True 只做改名、不打开文件）。轮转失败（如卷
    上遗留 root 属主的备份）只告警，不能阻断启动。
    """
    try:
        if not LOG_PATH.exists() or LOG_PATH.stat().st_size == 0:
            return
        handler = RotatingFileHandler(
            LOG_PATH,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
            delay=True,
        )
        try:
            handler.doRollover()
        finally:
            handler.close()
    except OSError as e:
        # logging 尚未配置：lastResort 处理器会把 WARNING 打到 stderr
        logging.getLogger(__name__).warning("Boot log rotation failed: %s", e)


def setup_logger(level: int = logging.INFO, reset: bool = False):
    global _listener

    level = logging.DEBUG if settings.log.debug_enable else level
    LOG_ROOT.mkdir(exist_ok=True)

    if reset:
        rotate_boot_log()

    logging.addLevelName(logging.DEBUG, "DEBUG:")
    logging.addLevelName(logging.INFO, "INFO:")
    logging.addLevelName(logging.WARNING, "WARNING:")
    LOGGING_FORMAT = "[%(asctime)s] %(levelname)-8s  %(message)s"
    TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(LOGGING_FORMAT, datefmt=TIME_FORMAT)

    file_handler = RotatingFileHandler(
        LOG_PATH, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    log_queue: SimpleQueue = SimpleQueue()
    queue_handler = QueueHandler(log_queue)
    # QueueHandler.prepare() 会用 handler 的 formatter 预格式化 record.msg，
    # 不设置时落到默认的 "%(levelname)s:%(name)s:%(message)s"，导致每行出现
    # "INFO::module.x:" 这种重复前缀。这里显式声明为 "模块名: 消息"，
    # 模块来源只出现一次，由外层 formatter 补时间与级别。
    queue_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))

    _listener = QueueListener(
        log_queue, file_handler, stream_handler, respect_handler_level=True
    )
    _listener.start()
    atexit.register(_listener.stop)

    logging.basicConfig(
        level=level,
        handlers=[queue_handler],
    )

    # Suppress verbose HTTP request logs from httpx
    logging.getLogger("httpx").setLevel(logging.WARNING)
