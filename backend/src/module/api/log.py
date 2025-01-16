from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse

from module.conf import LOG_PATH
from module.models import APIResponse
from module.security.api import UNAUTHORIZED, get_current_user

router = APIRouter(prefix="/log", tags=["log"])


@router.get("", response_model=str, dependencies=[Depends(get_current_user)])
async def get_log():
    if not LOG_PATH.exists():
        return Response("Log file not found", status_code=404)
    with open(LOG_PATH, "rb") as f:
        return Response(f.read(), media_type="text/plain")


@router.get(
    "/clear", response_model=APIResponse, dependencies=[Depends(get_current_user)]
)
async def clear_log():
    if not LOG_PATH.exists():
        return JSONResponse(
            status_code=406,
            content={"msg_en": "Log file not found.", "msg_zh": "日志文件未找到。"},
        )
    LOG_PATH.write_text("")
    return JSONResponse(
        status_code=200,
        content={"msg_en": "Log cleared successfully.", "msg_zh": "日志清除成功。"},
    )
