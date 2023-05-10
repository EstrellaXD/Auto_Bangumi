import os
import logging
import uvicorn


from module.api import router
from module.conf import settings
from module.conf.uvicorn_logging import logging_config


logger = logging.getLogger(__name__)


if __name__ == "__main__":
    if not os.path.isdir("data"):
        os.mkdir("data")
    uvicorn.run(
        router, host="0.0.0.0", port=settings.program.webui_port,
        log_config=logging_config,
    )
