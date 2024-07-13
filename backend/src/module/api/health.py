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
    status = current_status
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
        logger.error(f"[Health] Health status changed from {current_status} to {status}")
        current_status = status
        return JSONResponse(
            status_code=200,
            content={"msg_en": "Health status updated successfully.", "msg_zh": "健康状态更新成功。"},
        )
    except Exception as e:
        logger.error(f"[Health] Health status updated failed: {str(e)}")
        return JSONResponse(
            status_code=406,
            content={"msg_en": "Health status updated failed.", "msg_zh": "健康状态更新失败。"},
        )