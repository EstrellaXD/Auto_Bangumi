from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse

from module.conf import LOG_PATH
from module.models import APIResponse
from module.security.api import get_current_user

router = APIRouter(prefix="/log", tags=["log"])


_TAIL_BYTES = 512 * 1024  # 512 KB


@router.get("", response_model=str, dependencies=[Depends(get_current_user)])
async def get_log():
    if LOG_PATH.exists():
        with open(LOG_PATH, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            if size > _TAIL_BYTES:
                f.seek(-_TAIL_BYTES, 2)
                data = f.read()
                # Drop first partial line
                idx = data.find(b"\n")
                if idx != -1:
                    data = data[idx + 1 :]
            else:
                f.seek(0)
                data = f.read()
            return Response(data, media_type="text/plain")
    else:
        return Response("Log file not found", status_code=404)


@router.post(
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
            status_code=404,
            content={"msg_en": "Log file not found.", "msg_zh": "日志文件未找到。"},
        )
