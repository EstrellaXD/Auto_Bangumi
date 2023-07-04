from fastapi import APIRouter

from .auth import router as auth_router
from .bangumi import router as bangumi_router
from .config import router as config_router
from .download import router as download_router
from .log import router as log_router
from .program import router as program_router

__all__ = "v1"

# API 1.0
v1 = APIRouter(prefix="/v1")
v1.include_router(auth_router)
v1.include_router(log_router)
v1.include_router(program_router)
v1.include_router(download_router)
v1.include_router(bangumi_router)
v1.include_router(config_router)