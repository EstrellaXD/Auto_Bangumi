import logging

from .json_config import save, load
from module.models import ProgramData

logger = logging.getLogger(__name__)


def load_program_data(path: str) -> ProgramData:
    data = load(path)
    try:
        data = ProgramData(**data)
        logger.info("Data file loaded")
    except Exception as e:
        logger.warning(
            "Data file is not compatible with the current version, rebuilding..."
        )
        logger.debug(e)
        data = ProgramData(
            rss_link=data["rss_link"],
            data_version=data["data_version"],
            bangumi_info=[],
        )
    return data


def save_program_data(path: str, data: ProgramData):
    save(path, data.dict())
    logger.debug("Data file saved")
