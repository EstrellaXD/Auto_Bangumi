from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse

from module.conf import LOG_PATH
from module.models import APIResponse
from module.security.api import get_current_user

router = APIRouter(prefix="/log", tags=["log"])


@router.get("", response_model=str, dependencies=[Depends(get_current_user)])
async def get_log():
    if LOG_PATH.exists():
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 只返回最后200行
            last_lines = lines[-200:] if len(lines) > 200 else lines
            content = "".join(last_lines)

            return Response(content, media_type="text/plain; charset=utf-8")

        except Exception as e:
            return Response(f"Error reading log file: {str(e)}", status_code=500)
    else:
        return Response("Log file not found", status_code=404)


@router.get(
    "/clear", response_model=APIResponse, dependencies=[Depends(get_current_user)]
)
async def clear_log():
    if LOG_PATH.exists():
        LOG_PATH.write_text("")
        return JSONResponse(
            status_code=200,
            content={"msg_en": "Log cleared successfully.", "msg_zh": "日志清除成功。"},
        )
    else:
        return JSONResponse(
            status_code=406,
            content={"msg_en": "Log file not found.", "msg_zh": "日志文件未找到。"},
        )
