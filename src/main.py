import threading
import logging

from module import app
from module import api
from module.conf import VERSION, setup_logger


logger = logging.getLogger(__name__)


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
    t = threading.Thread(target=app.run)
    t.daemon = True
    t.start()
    
    # API
    api.run()
