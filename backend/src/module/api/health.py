import logging
from module.api import program
from fastapi import APIRouter
from fastapi import HTTPException

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger(__name__)

@router.get("/")
def health_check():
    is_healthy = program.check_downloader_status()
    return {"status": "healthy" if is_healthy else "unhealthy"}

@router.patch("/")
def update_health_status(status: str):
    try:
        logger.error(f"[Health] Health status changed to ",status)
        return {"status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))