import logging
from datetime import datetime

from module.notification.base import DEFAULT_LOG_TEMPLATE


def make_template(record: logging.LogRecord) -> str:
    """Generates a template for logging messages based on the given LogRecord.

    Args:
        record (logging.LogRecord): The LogRecord object containing the log information.

    Returns:
        str: The template string for logging messages.
    """

    if hasattr(record, "asctime"):
        dt = record.asctime
    else:
        dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return DEFAULT_LOG_TEMPLATE.format(
        dt=dt,
        levelname=record.levelname,
        msg=record.msg,
    )
