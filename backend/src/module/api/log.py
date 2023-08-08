import os

from fastapi import APIRouter, Depends, HTTPException, Response, status

from module.conf import LOG_PATH
from module.security.api import get_current_user, UNAUTHORIZED

router = APIRouter(prefix="/log", tags=["log"])


@router.get("")
async def get_log(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    if LOG_PATH.exists():
        with open(LOG_PATH, "rb") as f:
            return Response(f.read(), media_type="text/plain")
    else:
        return Response("Log file not found", status_code=404)


@router.get("/clear")
async def clear_log(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    if LOG_PATH.exists():
        LOG_PATH.write_text("")
        return {"status": "ok"}
    else:
        return Response("Log file not found", status_code=404)
