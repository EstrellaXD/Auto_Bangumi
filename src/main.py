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
    }
}

if __name__ == "__main__":
    uvicorn.run(
        router, host="0.0.0.0", port=settings.program.webui_port,
        log_config=uvicorn_logging_config,
    )
