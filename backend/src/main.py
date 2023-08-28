import os

import logging
import uvicorn

from module.api import router
from module.conf import settings, setup_logger

setup_logger(reset=True)
logger = logging.getLogger(__name__)
uvicorn_logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": logger.handlers,
    "loggers": {
        "uvicorn": {
            "level": logger.level,
        },
        "uvicorn.access": {
            "level": "WARNING",
        },
    },
}

if __name__ == "__main__":
    host = "::" if os.getenv("IPV6") else "0.0.0.0"
    uvicorn.run(
        router,
        host=host,
        port=settings.program.webui_port,
        log_config=uvicorn_logging_config,
    )
