import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from module.conf import settings
from module.models import Config, APIResponse
from module.security.api import get_current_user, UNAUTHORIZED

router = APIRouter(prefix="/config", tags=["config"])
logger = logging.getLogger(__name__)


@router.get("/get", response_model=Config)
async def get_config(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    return settings


@router.patch("/update", response_model=APIResponse)
async def update_config(config: Config, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    try:
        settings.save(config_dict=config.dict())
        settings.load()
        # update_rss()
        logger.info("Config updated")
        return JSONResponse(
            status_code=200,
            content={"msg_en": "Update config successfully.", "msg_zh": "更新配置成功。"}
        )
    except Exception as e:
        logger.warning(e)
        return JSONResponse(
            status_code=406,
            content={"msg_en": "Update config failed.", "msg_zh": "更新配置失败。"}
        )
