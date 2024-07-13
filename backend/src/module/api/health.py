import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from core.status import ProgramStatus

from module.models import APIResponse

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger(__name__)

current_health_status = "healthy"

@router.get("", response_model=APIResponse)
async def health_check():
    health_status = current_health_status
    program_is_stopped = ProgramStatus.is_stopped
    if health_status == "unhealthy" or program_is_stopped:
      return JSONResponse(
            status_code=500,
            content={"status": health_status},
        )
    else:
      return JSONResponse(
            status_code=200,
            content={"status": health_status},
        )

@router.patch("", response_model=APIResponse)
async def update_health_status(status: str):
    global current_health_status
    try:
        logger.info(f"[Health] Health status changed from {current_health_status} to {status}")
        current_health_status = status
        return JSONResponse(
            status_code=200,
            content={"msg_en": "Health status updated successfully.", "msg_zh": "健康状态更新成功。"},
        )
    except Exception as e:
        logger.warning(f"[Health] Health status updated failed: {str(e)}")
        return JSONResponse(
            status_code=406,
            content={"msg_en": "Health status updated failed.", "msg_zh": "健康状态更新失败。"},
        )