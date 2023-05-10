from .bangumi import router

from module.conf import settings
from module.models import Config


@router.get("/api/v1/getConfig", tags=["config"], response_model=Config)
async def get_config():
    return settings


# Reverse proxy
@router.post("/api/v1/updateConfig", tags=["config"], response_model=Config)
async def update_config(config: Config):
    settings.save(config_dict=config.dict())
    return settings
