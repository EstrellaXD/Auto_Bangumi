import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from module.core.status import ProgramStatus
from module.models import APIResponse

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger(__name__)

current_health_status = "healthy"

@router.get("", response_model=APIResponse)
async def health_check():
    global current_health_status
    program_is_running = ProgramStatus.is_running
    logger.debug(f"[Health] Health status is {current_health_status} , ProgramStatus is {program_is_running}")
    if current_health_status == "healthy" and program_is_running:
      return JSONResponse(
            status_code=200,
            content={"status": "healthy"},
        )
    else:
      current_health_status = "unhealthy"
      return JSONResponse(
            status_code=500,
            content={"status": "unhealthy"},
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