import logging
import multiprocessing

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
    num_processes = 2
    processes = []
    p1 = multiprocessing.Process(target=app.run)
    p2 = multiprocessing.Process(target=api.run)
    process_list = [p1, p2]
    for p in process_list:
        p.start()
        processes.append(p)
    for p in processes:
        p.join()

