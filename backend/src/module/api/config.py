import logging

from fastapi import APIRouter, Depends, HTTPException, status

from module.conf import settings
from module.models import Config
from module.security.api import get_current_user, UNAUTHORIZED

router = APIRouter(tags=["config"])
logger = logging.getLogger(__name__)


@router.get("/getConfig", response_model=Config)
async def get_config(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    return settings.dict()


@router.post("/updateConfig")
async def update_config(config: Config, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    try:
        settings.save(config_dict=config.dict())
        settings.load()
        logger.info("Config updated")
        return {"message": "Success"}
    except Exception as e:
        logger.warning(e)
        return {"message": "Failed to update config"}
