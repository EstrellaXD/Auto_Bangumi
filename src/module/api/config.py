import logging

from .bangumi import router

from module.conf import settings
from module.models import Config

logger = logging.getLogger(__name__)


@router.get("/api/v1/getConfig", tags=["config"], response_model=Config)
async def get_config():
    return settings


@router.post("/api/v1/updateConfig", tags=["config"])
async def update_config(config: Config):
    try:
        settings.save(config_dict=config.dict())
        settings.load()
        logger.info("Config updated")
        return {"message": "Success"}
    except Exception as e:
        logger.warning(e)
        return {"message": "Failed to update config"}
