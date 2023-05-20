import os
from fastapi import Response, HTTPException, Depends, status

from .auth import router

from module.conf import LOG_PATH
from module.security import get_current_user


@router.get("/api/v1/log", tags=["log"])
async def get_log(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    if os.path.isfile(LOG_PATH):
        with open(LOG_PATH, "r") as f:
            return Response(f.read(), media_type="text/plain")
    else:
        return Response("Log file not found", status_code=404)


@router.get("/api/v1/log/clear", tags=["log"])
async def clear_log(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    if os.path.isfile(LOG_PATH):
        with open(LOG_PATH, "w") as f:
            f.write("")
        return {"status": "ok"}
    else:
        return Response("Log file not found", status_code=404)
