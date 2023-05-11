import logging
import uvicorn

from module.api import router
from module.conf import settings, setup_logger

log_level = logging.DEBUG if settings.log.debug_enable else logging.INFO
setup_logger(log_level, reset=True)
logger = logging.getLogger(__name__)
uvicorn_logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": logger.handlers,
    "loggers": {
        "uvicorn": {
            "level": log_level,
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
