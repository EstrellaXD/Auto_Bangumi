import logging
from module.api import program
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from module.models import APIResponse

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger(__name__)

current_status = "healthy"

@router.get("/", response_model=APIResponse)
async def health_check():
    is_healthy = program.check_downloader_status()
    status = "unhealthy" if not is_healthy else current_status
    if status == "unhealthy":
      return JSONResponse(
            status_code=500,
            content={"status": status},
        )
    else:
      return JSONResponse(
            status_code=200,
            content={"status": status},
        )

@router.patch("/")
async def update_health_status(status: str):
    global current_status
    try:
        logger.error(f"[Health] Health status changed to ",status)
        current_status = status
        return {"status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))