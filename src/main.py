import os
import signal
import logging
import multiprocessing
import uvicorn

from module import app
from module.api import router
from module.conf import VERSION, setup_logger, settings


logger = logging.getLogger(__name__)

main_process = multiprocessing.Process(target=app.run)


@router.get("/api/v1/restart")
async def restart():
    global main_process
    logger.info("Restarting...")
    os.kill(main_process.pid, signal.SIGTERM)
    main_process = multiprocessing.Process(target=app.run)
    main_process.start()
    logger.info("Restarted")
    return {"status": "success"}


def show_info():
    with open("icon", "r") as f:
        for line in f.readlines():
            logger.info(line.strip("\n"))
    logger.info(f"Version {VERSION}  Author: EstrellaXD Twitter: https://twitter.com/Estrella_Pan")
    logger.info("GitHub: https://github.com/EstrellaXD/Auto_Bangumi/")
    logger.info("Starting AutoBangumi...")


if __name__ == "__main__":
    setup_logger()
    show_info()
    main_process.start()
    uvicorn.run(router, host="0.0.0.0", port=settings.program.webui_port)

